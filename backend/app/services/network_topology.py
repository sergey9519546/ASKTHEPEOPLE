import networkx as nx
from typing import Dict, Any, List
import logging
import asyncio
from app.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

def apply_network_topology(agent_graph: Any, config: Dict[str, Any]):
    """
    Applies a network topology to the given agent graph based on simulation config.
    Supports: small-world, scale-free, random, complete.
    """
    topology_config = config.get("network_topology", {})
    if not topology_config:
        return
        
    topology_type = topology_config.get("type", "none")
    if topology_type == "none":
        return
        
    agents = agent_graph.get_agents()
    agent_ids = [agent_id for agent_id, _ in agents]
    n = len(agent_ids)
    
    if n <= 1:
        return
        
    # Clear existing edges
    edges = agent_graph.get_edges()
    for u, v in edges:
        agent_graph.remove_edge(u, v)
        
    nx_graph = None
    if topology_type == "small-world":
        k = topology_config.get("k", min(4, n-1))
        p = topology_config.get("p", 0.1)
        nx_graph = nx.watts_strogatz_graph(n, k, p)
    elif topology_type == "scale-free":
        m = topology_config.get("m", min(2, n-1))
        nx_graph = nx.barabasi_albert_graph(n, m)
    elif topology_type == "random":
        p = topology_config.get("p", 0.1)
        nx_graph = nx.erdos_renyi_graph(n, p)
    elif topology_type == "complete":
        nx_graph = nx.complete_graph(n)
        
    if nx_graph is not None:
        for u, v in nx_graph.edges():
            agent_graph.add_edge(agent_ids[u], agent_ids[v])
            agent_graph.add_edge(agent_ids[v], agent_ids[u])
        logger.info(f"Applied {topology_type} topology with {n} nodes and {nx_graph.number_of_edges()} edges.")


async def apply_homophily_rewiring(agent_graph: Any, simulation_dir: str, round_num: int, config: Dict[str, Any]):
    """
    Evaluates agent reflections for homophily and removes edges between disagreeable peers.
    Simulates emergent filter bubbles.
    """
    rewiring_config = config.get("homophily_rewiring", {})
    if not rewiring_config.get("enabled", False):
        return
        
    # Fetch recent reflections for all agents to determine their current stance
    import sqlite3
    import os
    db_path = os.path.join(simulation_dir, "simulation_observations.db")
    if not os.path.exists(db_path):
        return
        
    agent_reflections = {}
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get latest reflection for each agent
        cursor.execute("""
            SELECT agent_name, synthesis_text
            FROM reflections
            WHERE round_num <= ?
            ORDER BY round_num DESC, id DESC
        """, (round_num,))
        
        for row in cursor.fetchall():
            agent_name, text = row
            if agent_name not in agent_reflections:
                agent_reflections[agent_name] = text
        conn.close()
    except Exception as e:
        logger.error(f"Failed to fetch reflections for homophily rewiring: {e}")
        return

    if len(agent_reflections) < 2:
        return

    # Use routine model for cheap batch evaluation
    llm = LLMClient()
    
    # We will sample edges to review, rather than all edges, to bound latency
    edges = agent_graph.get_edges()
    import random
    sample_size = min(len(edges), rewiring_config.get("max_edges_to_evaluate", 20))
    edges_to_evaluate = random.sample(edges, sample_size)
    
    removed_count = 0
    agents = dict(agent_graph.get_agents())

    for u, v in edges_to_evaluate:
        agent_u = agents.get(u)
        agent_v = agents.get(v)
        if not agent_u or not agent_v:
            continue
            
        name_u = getattr(agent_u, 'name', f'Agent_{u}')
        name_v = getattr(agent_v, 'name', f'Agent_{v}')
        
        ref_u = agent_reflections.get(name_u)
        ref_v = agent_reflections.get(name_v)
        
        if not ref_u or not ref_v:
            continue
            
        prompt = f"""
        Agent A reflection: {ref_u}
        Agent B reflection: {ref_v}
        
        Are these two agents fundamentally disagreeable or opposed on their core stances such that Agent A would unfollow Agent B to curate their feed?
        Respond with ONLY 'YES' or 'NO'.
        """
        try:
            # We use complexity="routine" to hit the faster/cheaper model for these bulk checks
            response = llm.chat(prompt, complexity="routine").strip().upper()
            if "YES" in response:
                agent_graph.remove_edge(u, v)
                removed_count += 1
                logger.info(f"Homophily rewiring: {name_u} unfollowed {name_v}")
        except Exception as e:
            logger.error(f"LLM error during homophily evaluation: {e}")
            
    if removed_count > 0:
        logger.info(f"Homophily rewiring complete: Removed {removed_count} edges in round {round_num}.")
