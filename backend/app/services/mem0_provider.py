"""
Mem0 Memory Provider
Implements MemoryProvider using the mem0ai SDK (platform or OSS mode).
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .memory_provider import (
    AgentInterview,
    EdgeInfo,
    EntityNode,
    FilteredEntities,
    InsightForgeResult,
    InterviewResult,
    MemoryProvider,
    NodeInfo,
    PanoramaResult,
    SearchResult,
)

logger = get_logger("mirofish.mem0_provider")


# ---------------------------------------------------------------------------
# Mem0MemoryUpdater
# ---------------------------------------------------------------------------

@dataclass
class Mem0MemoryUpdater:
    """
    Buffers agent activity dicts and periodically flushes them to Mem0.

    Attributes
    ----------
    simulation_id : str
        Identifies which simulation this updater belongs to.
    graph_id : str
        The Mem0 user_id (isolation key) to write memories under.
    client : object
        A mem0 MemoryClient or Memory instance.
    _buffer : list
        Internal activity buffer.
    _lock : threading.Lock
        Protects _buffer for concurrent access.
    _running : bool
        Controls the background flush thread.
    """

    simulation_id: str
    graph_id: str
    client: Any  # MemoryClient or Memory

    # mutable defaults must use field()
    _buffer: List[Dict[str, Any]] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _running: bool = field(default=False)

    BATCH_SIZE: int = field(default=5, init=False)
    FLUSH_INTERVAL: int = field(default=10, init=False)  # seconds

    # stats
    _total_added: int = field(default=0, init=False)
    _total_flushed: int = field(default=0, init=False)
    _total_failed: int = field(default=0, init=False)
    _skipped: int = field(default=0, init=False)

    # background thread (not part of __init__ signature)
    _thread: Optional[threading.Thread] = field(default=None, init=False)

    def start(self) -> None:
        """Start the background periodic-flush thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._periodic_flush,
            daemon=True,
            name=f"Mem0Updater-{self.simulation_id[:8]}",
        )
        self._thread.start()
        logger.info(
            "Mem0MemoryUpdater started: simulation_id=%s graph_id=%s",
            self.simulation_id,
            self.graph_id,
        )

    def stop(self) -> None:
        """Stop the background thread and flush remaining items."""
        self._running = False
        self._flush_remaining()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=15)
        logger.info(
            "Mem0MemoryUpdater stopped: simulation_id=%s added=%d flushed=%d failed=%d skipped=%d",
            self.simulation_id,
            self._total_added,
            self._total_flushed,
            self._total_failed,
            self._skipped,
        )

    def add_activity_from_dict(self, data: Dict[str, Any], platform: str) -> None:
        """
        Queue one activity dict for later flush.

        Skips entries that are event-type markers or DO_NOTHING actions.
        """
        if "event_type" in data:
            return
        action_type = data.get("action_type", "")
        if action_type == "DO_NOTHING":
            self._skipped += 1
            return

        entry = dict(data)
        entry["_platform"] = platform
        with self._lock:
            self._buffer.append(entry)
            self._total_added += 1

        logger.debug(
            "Mem0Updater queued activity: agent=%s action=%s",
            data.get("agent_name", "?"),
            action_type,
        )

        # Eager flush when buffer reaches BATCH_SIZE
        batch = None
        with self._lock:
            if len(self._buffer) >= self.BATCH_SIZE:
                batch = self._buffer[: self.BATCH_SIZE]
                self._buffer = self._buffer[self.BATCH_SIZE :]

        if batch:
            self._flush_batch(batch)

    def _format_activity(self, data: Dict[str, Any]) -> str:
        """Convert an activity dict to a natural-language string for Mem0."""
        agent_name = data.get("agent_name", "Unknown")
        action_type = data.get("action_type", "")
        action_args = data.get("action_args", {})
        platform = data.get("_platform", "")

        descriptions: Dict[str, Any] = {
            "CREATE_POST": lambda: f"posted: \"{action_args.get('content', '')}\"",
            "LIKE_POST": lambda: (
                f"liked {action_args.get('post_author_name', 'someone')}'s post: "
                f"\"{action_args.get('post_content', '')}\""
                if action_args.get("post_content")
                else f"liked a post by {action_args.get('post_author_name', 'someone')}"
            ),
            "DISLIKE_POST": lambda: (
                f"disliked {action_args.get('post_author_name', 'someone')}'s post: "
                f"\"{action_args.get('post_content', '')}\""
                if action_args.get("post_content")
                else "disliked a post"
            ),
            "REPOST": lambda: (
                f"reposted {action_args.get('original_author_name', 'someone')}'s post: "
                f"\"{action_args.get('original_content', '')}\""
                if action_args.get("original_content")
                else "reposted a post"
            ),
            "QUOTE_POST": lambda: (
                f"quoted {action_args.get('original_author_name', 'someone')}'s post "
                f"\"{action_args.get('original_content', '')}\" "
                f"with comment: \"{action_args.get('content', '')}\""
            ),
            "FOLLOW": lambda: f"followed user \"{action_args.get('target_user_name', 'someone')}\"",
            "CREATE_COMMENT": lambda: (
                f"commented \"{action_args.get('content', '')}\" "
                f"on {action_args.get('post_author_name', 'someone')}'s post"
                if action_args.get("post_author_name")
                else f"commented: \"{action_args.get('content', '')}\""
            ),
            "LIKE_COMMENT": lambda: (
                f"liked {action_args.get('comment_author_name', 'someone')}'s comment: "
                f"\"{action_args.get('comment_content', '')}\""
                if action_args.get("comment_content")
                else "liked a comment"
            ),
            "DISLIKE_COMMENT": lambda: (
                f"disliked {action_args.get('comment_author_name', 'someone')}'s comment"
            ),
            "SEARCH_POSTS": lambda: f"searched for posts: \"{action_args.get('query', action_args.get('keyword', ''))}\"",
            "SEARCH_USER": lambda: f"searched for user: \"{action_args.get('query', action_args.get('username', ''))}\"",
            "MUTE": lambda: f"muted user \"{action_args.get('target_user_name', 'someone')}\"",
            "REFRESH": lambda: "refreshed their feed",
            "TREND": lambda: "checked trending topics",
        }

        desc_fn = descriptions.get(action_type)
        desc = desc_fn() if desc_fn else f"performed {action_type}"

        platform_tag = f" [{platform}]" if platform else ""
        round_tag = f" (round {data.get('round', '?')})" if data.get("round") else ""
        return f"{agent_name}{platform_tag}{round_tag}: {desc}"

    def _flush_batch(self, batch: List[Dict[str, Any]]) -> None:
        """Send a batch of activities to Mem0 as a single add() call."""
        if not batch:
            return

        lines = [self._format_activity(item) for item in batch]
        combined = "\n".join(lines)
        messages = [{"role": "user", "content": combined}]

        try:
            _mem0_add(self.client, messages, self.graph_id)
            self._total_flushed += len(batch)
            logger.info(
                "Mem0Updater flushed %d activities for graph_id=%s",
                len(batch),
                self.graph_id,
            )
        except Exception as exc:
            self._total_failed += len(batch)
            logger.error(
                "Mem0Updater flush failed for graph_id=%s: %s",
                self.graph_id,
                exc,
            )

    def _flush_remaining(self) -> None:
        """Flush whatever is left in the buffer, regardless of size."""
        with self._lock:
            remaining = list(self._buffer)
            self._buffer = []

        if remaining:
            logger.info(
                "Mem0Updater flushing %d remaining activities on stop", len(remaining)
            )
            # Send in sub-batches of BATCH_SIZE
            for i in range(0, len(remaining), self.BATCH_SIZE):
                self._flush_batch(remaining[i : i + self.BATCH_SIZE])

    def _periodic_flush(self) -> None:
        """Background loop: flush buffer every FLUSH_INTERVAL seconds."""
        while self._running:
            time.sleep(self.FLUSH_INTERVAL)
            with self._lock:
                if len(self._buffer) == 0:
                    continue
                batch = list(self._buffer)
                self._buffer = []
            self._flush_batch(batch)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            buf_size = len(self._buffer)
        return {
            "simulation_id": self.simulation_id,
            "graph_id": self.graph_id,
            "batch_size": self.BATCH_SIZE,
            "flush_interval": self.FLUSH_INTERVAL,
            "total_added": self._total_added,
            "total_flushed": self._total_flushed,
            "total_failed": self._total_failed,
            "skipped": self._skipped,
            "buffer_size": buf_size,
            "running": self._running,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _mem0_add(client: Any, messages: List[Dict[str, str]], user_id: str, metadata: Optional[Dict] = None) -> List[Dict]:
    """
    Unified add() wrapper that handles both MemoryClient (platform) and Memory (OSS).
    Returns list of result dicts.
    """
    try:
        # Platform MemoryClient: add(messages, user_id=..., metadata=...)
        kwargs: Dict[str, Any] = {"user_id": user_id}
        if metadata:
            kwargs["metadata"] = metadata
        result = client.add(messages, **kwargs)
        if isinstance(result, list):
            return result
        # Some versions wrap in {"results": [...]}
        if isinstance(result, dict) and "results" in result:
            return result["results"]
        return []
    except Exception as exc:
        logger.error("mem0 add() failed for user_id=%s: %s", user_id, exc)
        raise


def _mem0_search(client: Any, query: str, user_id: str, top_k: int = 10, mode: str = "platform") -> List[Dict]:
    """
    Unified search() wrapper.
    Returns list of memory dicts.
    """
    try:
        if mode == "platform":
            # Platform: search(query, filters={"user_id": ...}, top_k=...)
            result = client.search(query, filters={"user_id": user_id}, top_k=top_k)
        else:
            # OSS: search(query, user_id=..., limit=...)
            result = client.search(query, user_id=user_id, limit=top_k)

        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("results", [])
        return []
    except Exception as exc:
        logger.error("mem0 search() failed for user_id=%s query='%s': %s", user_id, query, exc)
        raise


def _mem0_get_all(client: Any, user_id: str, mode: str = "platform") -> List[Dict]:
    """
    Unified get_all() wrapper.
    Returns list of memory dicts.
    """
    try:
        if mode == "platform":
            # Platform: get_all(filters={"user_id": ...}, page_size=...)
            result = client.get_all(filters={"user_id": user_id}, page_size=1000)
        else:
            # OSS: get_all(user_id=...)
            result = client.get_all(user_id=user_id)

        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("results", [])
        return []
    except Exception as exc:
        logger.error("mem0 get_all() failed for user_id=%s: %s", user_id, exc)
        raise


def _mem0_delete_all(client: Any, user_id: str, mode: str = "platform") -> None:
    """Unified delete_all() wrapper."""
    try:
        client.delete_all(user_id=user_id)
    except Exception as exc:
        logger.error("mem0 delete_all() failed for user_id=%s: %s", user_id, exc)
        raise


def _memory_to_node(mem: Dict[str, Any]) -> NodeInfo:
    """Convert a Mem0 memory dict to a NodeInfo."""
    mem_id = mem.get("id", "")
    content = mem.get("memory", "")
    categories = mem.get("categories") or []
    return NodeInfo(
        uuid=mem_id,
        name=content[:80] if content else mem_id,
        labels=categories if isinstance(categories, list) else [str(categories)],
        summary=content,
        attributes={
            "user_id": mem.get("user_id", ""),
            "created_at": mem.get("created_at", ""),
            "updated_at": mem.get("updated_at", ""),
            "metadata": mem.get("metadata", {}),
        },
    )


def _relation_to_edge(rel: Dict[str, Any], mem_id: str) -> EdgeInfo:
    """Convert a relation dict embedded in a Mem0 memory to an EdgeInfo."""
    source = rel.get("source", "")
    target = rel.get("target", "")
    relation = rel.get("relation", "")
    return EdgeInfo(
        uuid=f"{mem_id}:{source}:{relation}:{target}",
        name=relation,
        fact=f"{source} {relation} {target}",
        source_node_uuid=source,
        target_node_uuid=target,
        source_node_name=source,
        target_node_name=target,
    )


# ---------------------------------------------------------------------------
# Mem0Provider
# ---------------------------------------------------------------------------

class Mem0Provider(MemoryProvider):
    """
    MemoryProvider implementation backed by the mem0ai SDK.

    Supports both platform mode (MemoryClient) and OSS mode (Memory).
    The mode is selected automatically based on Config.MEM0_API_KEY:
      - If MEM0_API_KEY is set  -> platform MemoryClient
      - Otherwise               -> OSS Memory (requires OPENAI_API_KEY or custom config)
    """

    def __init__(self) -> None:
        self._client = self._build_client()
        # In-memory store for graph metadata (name, ontology)
        self._graphs: Dict[str, Dict[str, Any]] = {}
        # Active memory updaters keyed by simulation_id
        self._updaters: Dict[str, Mem0MemoryUpdater] = {}
        self._updaters_lock = threading.Lock()
        # LLM client for insight_forge sub-query generation
        self._llm: Optional[LLMClient] = None
        logger.info("Mem0Provider initialized (mode=%s)", self._mode)

    # ------------------------------------------------------------------
    # Client construction
    # ------------------------------------------------------------------

    def _build_client(self) -> Any:
        api_key = Config.MEM0_API_KEY
        if api_key:
            # Platform mode
            try:
                from mem0 import MemoryClient
                self._mode = "platform"
                client = MemoryClient(api_key=api_key)
                logger.info("Mem0 platform MemoryClient created")
                return client
            except ImportError:
                raise ImportError(
                    "mem0ai package is not installed. Run: pip install mem0ai"
                )
        else:
            # OSS mode
            try:
                from mem0 import Memory
                self._mode = "oss"
                client = Memory()
                logger.info("Mem0 OSS Memory client created")
                return client
            except ImportError:
                raise ImportError(
                    "mem0ai package is not installed. Run: pip install mem0ai"
                )

    def _get_llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    # ------------------------------------------------------------------
    # Graph Building
    # ------------------------------------------------------------------

    def create_graph(self, name: str) -> str:
        """
        Generate a stable graph_id (used as Mem0 user_id) and store metadata.
        """
        graph_id = f"mirofish_{uuid.uuid4().hex}"
        self._graphs[graph_id] = {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "ontology": None,
        }
        logger.info("Mem0Provider: created graph name='%s' graph_id=%s", name, graph_id)
        return graph_id

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> None:
        """Store ontology in-memory for later use as extraction guidance."""
        if graph_id not in self._graphs:
            self._graphs[graph_id] = {}
        self._graphs[graph_id]["ontology"] = ontology
        logger.info("Mem0Provider: ontology set for graph_id=%s", graph_id)

    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback=None,
    ) -> List[str]:
        """
        Add text chunks to Mem0 in batches.
        Returns a list of memory IDs (or chunk indices as fallback).
        """
        ids: List[str] = []
        total = len(chunks)
        logger.info(
            "Mem0Provider: adding %d chunks to graph_id=%s (batch_size=%d)",
            total,
            graph_id,
            batch_size,
        )

        for batch_start in range(0, total, batch_size):
            batch = chunks[batch_start : batch_start + batch_size]
            combined_text = "\n\n".join(batch)
            messages = [{"role": "user", "content": combined_text}]

            try:
                results = _mem0_add(self._client, messages, graph_id)
                for r in results:
                    if isinstance(r, dict) and r.get("id"):
                        ids.append(r["id"])
                    else:
                        ids.append(f"{graph_id}:{batch_start}")
            except Exception as exc:
                logger.error(
                    "Mem0Provider: failed to add batch starting at %d: %s",
                    batch_start,
                    exc,
                )
                ids.append(f"error:{batch_start}")

            if progress_callback:
                done = min(batch_start + batch_size, total)
                ratio = done / total if total > 0 else 1.0
                try:
                    progress_callback(
                        f"Added {done}/{total} chunks to Mem0",
                        ratio,
                    )
                except Exception:
                    pass

        logger.info(
            "Mem0Provider: finished adding chunks to graph_id=%s, ids=%d",
            graph_id,
            len(ids),
        )
        return ids

    def wait_for_processing(
        self,
        identifiers: List[str],
        progress_callback=None,
        timeout: int = 600,
    ) -> None:
        """No-op: Mem0 processes synchronously."""
        logger.debug("Mem0Provider: wait_for_processing is a no-op (synchronous)")

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """Fetch all memories and return graph-like summary."""
        try:
            memories = _mem0_get_all(self._client, graph_id, mode=self._mode)
        except Exception as exc:
            logger.error("Mem0Provider: get_graph_data failed for graph_id=%s: %s", graph_id, exc)
            memories = []

        nodes = []
        edges = []
        for mem in memories:
            nodes.append(_memory_to_node(mem).to_dict())
            for rel in mem.get("relations", []) or []:
                edges.append(_relation_to_edge(rel, mem.get("id", "")).to_dict())

        return {
            "graph_id": graph_id,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def delete_graph(self, graph_id: str) -> None:
        """Delete all memories for this graph_id and remove local metadata."""
        try:
            _mem0_delete_all(self._client, graph_id, mode=self._mode)
            logger.info("Mem0Provider: deleted all memories for graph_id=%s", graph_id)
        except Exception as exc:
            logger.error("Mem0Provider: delete_graph failed for graph_id=%s: %s", graph_id, exc)

        self._graphs.pop(graph_id, None)

    # ------------------------------------------------------------------
    # Entity Reading
    # ------------------------------------------------------------------

    def filter_defined_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True,
    ) -> FilteredEntities:
        """
        Build entity nodes from Mem0 memories.
        Uses relation triples to derive entity names/types.
        """
        try:
            memories = _mem0_get_all(self._client, graph_id, mode=self._mode)
        except Exception as exc:
            logger.error("Mem0Provider: filter_defined_entities failed: %s", exc)
            memories = []

        # Collect unique entities from relation triples
        entity_map: Dict[str, EntityNode] = {}
        for mem in memories:
            mem_id = mem.get("id", "")
            categories = mem.get("categories") or []
            if isinstance(categories, str):
                categories = [categories]

            for rel in mem.get("relations", []) or []:
                for role in ("source", "target"):
                    name = rel.get(role, "")
                    if not name:
                        continue
                    if name not in entity_map:
                        # Derive label from categories or relation
                        labels = list(categories) if categories else ["Entity"]
                        entity_map[name] = EntityNode(
                            uuid=f"{graph_id}:{name}",
                            name=name,
                            labels=labels,
                            summary=mem.get("memory", ""),
                            attributes={"memory_id": mem_id},
                            related_edges=[],
                            related_nodes=[],
                        )
                    # Enrich with edge info
                    if enrich_with_edges:
                        edge_fact = f"{rel.get('source', '')} {rel.get('relation', '')} {rel.get('target', '')}"
                        entity_map[name].related_edges.append({"fact": edge_fact})

        # Optionally filter by type
        if defined_entity_types:
            type_set = set(t.lower() for t in defined_entity_types)
            filtered = [
                e for e in entity_map.values()
                if any(lbl.lower() in type_set for lbl in e.labels)
            ]
        else:
            filtered = list(entity_map.values())

        entity_types = list(
            {lbl for e in filtered for lbl in e.labels if lbl not in ("Entity", "Node")}
        )

        return FilteredEntities(
            entities=filtered,
            entity_types=entity_types,
            total_count=len(entity_map),
            filtered_count=len(filtered),
        )

    def get_entity_with_context(
        self, graph_id: str, entity_uuid: str
    ) -> Optional[EntityNode]:
        """
        Search for the entity by name (last segment of uuid) and return enriched node.
        """
        # entity_uuid format: "{graph_id}:{name}"
        entity_name = entity_uuid.split(":")[-1] if ":" in entity_uuid else entity_uuid
        try:
            memories = _mem0_search(self._client, entity_name, graph_id, top_k=20, mode=self._mode)
        except Exception as exc:
            logger.error("Mem0Provider: get_entity_with_context search failed: %s", exc)
            return None

        if not memories:
            return None

        related_edges: List[Dict] = []
        related_nodes: List[Dict] = []
        summary_parts: List[str] = []

        for mem in memories:
            content = mem.get("memory", "")
            if content:
                summary_parts.append(content)
            for rel in mem.get("relations", []) or []:
                fact = f"{rel.get('source', '')} {rel.get('relation', '')} {rel.get('target', '')}"
                related_edges.append({"fact": fact, "memory_id": mem.get("id", "")})
                other = rel.get("target") if rel.get("source") == entity_name else rel.get("source")
                if other:
                    related_nodes.append({"name": other})

        return EntityNode(
            uuid=entity_uuid,
            name=entity_name,
            labels=["Entity"],
            summary="; ".join(summary_parts[:3]),
            attributes={"graph_id": graph_id},
            related_edges=related_edges,
            related_nodes=related_nodes,
        )

    def get_entities_by_type(
        self, graph_id: str, entity_type: str
    ) -> List[EntityNode]:
        """Search for entities of a given type by querying Mem0."""
        try:
            memories = _mem0_search(self._client, entity_type, graph_id, top_k=50, mode=self._mode)
        except Exception as exc:
            logger.error("Mem0Provider: get_entities_by_type failed: %s", exc)
            return []

        entity_map: Dict[str, EntityNode] = {}
        for mem in memories:
            for rel in mem.get("relations", []) or []:
                for role in ("source", "target"):
                    name = rel.get(role, "")
                    if name and name not in entity_map:
                        entity_map[name] = EntityNode(
                            uuid=f"{graph_id}:{name}",
                            name=name,
                            labels=[entity_type, "Entity"],
                            summary=mem.get("memory", ""),
                            attributes={"memory_id": mem.get("id", "")},
                        )
        return list(entity_map.values())

    # ------------------------------------------------------------------
    # Memory Updater (Simulation)
    # ------------------------------------------------------------------

    def create_memory_updater(self, simulation_id: str, graph_id: str) -> None:
        """Create and start a Mem0MemoryUpdater for the given simulation."""
        with self._updaters_lock:
            # Stop existing updater for this simulation if any
            if simulation_id in self._updaters:
                try:
                    self._updaters[simulation_id].stop()
                except Exception as exc:
                    logger.warning(
                        "Mem0Provider: error stopping old updater for simulation_id=%s: %s",
                        simulation_id,
                        exc,
                    )

            updater = Mem0MemoryUpdater(
                simulation_id=simulation_id,
                graph_id=graph_id,
                client=self._client,
            )
            updater.start()
            self._updaters[simulation_id] = updater

        logger.info(
            "Mem0Provider: memory updater created for simulation_id=%s graph_id=%s",
            simulation_id,
            graph_id,
        )

    def stop_memory_updater(self, simulation_id: str) -> None:
        """Stop the updater for the given simulation and flush remaining data."""
        with self._updaters_lock:
            updater = self._updaters.pop(simulation_id, None)

        if updater:
            updater.stop()
            logger.info(
                "Mem0Provider: memory updater stopped for simulation_id=%s", simulation_id
            )
        else:
            logger.warning(
                "Mem0Provider: no updater found for simulation_id=%s", simulation_id
            )

    def get_memory_updater(self, simulation_id: str) -> Optional[Mem0MemoryUpdater]:
        """Return the updater instance for the given simulation, or None."""
        return self._updaters.get(simulation_id)

    def stop_all_memory_updaters(self) -> None:
        """Stop and remove every active memory updater."""
        with self._updaters_lock:
            sim_ids = list(self._updaters.keys())

        for sim_id in sim_ids:
            with self._updaters_lock:
                updater = self._updaters.pop(sim_id, None)
            if updater:
                try:
                    updater.stop()
                except Exception as exc:
                    logger.error(
                        "Mem0Provider: error stopping updater for simulation_id=%s: %s",
                        sim_id,
                        exc,
                    )

        logger.info("Mem0Provider: all memory updaters stopped")

    # ------------------------------------------------------------------
    # Search & Analysis Tools
    # ------------------------------------------------------------------

    def search_graph(self, graph_id: str, query: str, limit: int = 10) -> SearchResult:
        """Semantic search using Mem0's vector search."""
        try:
            memories = _mem0_search(self._client, query, graph_id, top_k=limit, mode=self._mode)
        except Exception as exc:
            logger.error("Mem0Provider: search_graph failed for graph_id=%s: %s", graph_id, exc)
            return SearchResult(facts=[], edges=[], nodes=[], query=query, total_count=0)

        facts: List[str] = []
        edges: List[Dict] = []
        nodes: List[Dict] = []

        for mem in memories:
            content = mem.get("memory", "")
            if content:
                facts.append(content)
            nodes.append(_memory_to_node(mem).to_dict())
            for rel in mem.get("relations", []) or []:
                fact = f"{rel.get('source', '')} {rel.get('relation', '')} {rel.get('target', '')}"
                edges.append({"fact": fact, "source": rel.get("source"), "target": rel.get("target"), "relation": rel.get("relation")})

        return SearchResult(
            facts=facts,
            edges=edges,
            nodes=nodes,
            query=query,
            total_count=len(facts),
        )

    def insight_forge(
        self,
        graph_id: str,
        query: str,
        simulation_requirement: str,
        report_context: str = "",
        max_sub_queries: int = 5,
    ) -> InsightForgeResult:
        """
        Deep multi-dimensional search:
        1. Use LLM to decompose the query into sub-queries.
        2. Execute each sub-query against Mem0.
        3. Aggregate unique facts, entities, and relationship chains.
        """
        # Step 1: Generate sub-queries via LLM
        sub_queries = self._generate_sub_queries(
            query, simulation_requirement, report_context, max_sub_queries
        )

        # Step 2: Multi-search
        seen_facts: Dict[str, bool] = {}
        all_facts: List[str] = []
        entity_map: Dict[str, Dict[str, Any]] = {}
        relationship_chains: List[str] = []

        for sq in [query] + sub_queries:
            try:
                result = self.search_graph(graph_id, sq, limit=10)
            except Exception as exc:
                logger.warning("Mem0Provider: insight_forge sub-query '%s' failed: %s", sq, exc)
                continue

            for fact in result.facts:
                if fact not in seen_facts:
                    seen_facts[fact] = True
                    all_facts.append(fact)

            for edge in result.edges:
                chain = edge.get("fact", "")
                if chain and chain not in relationship_chains:
                    relationship_chains.append(chain)

            for node in result.nodes:
                nid = node.get("uuid", node.get("name", ""))
                if nid and nid not in entity_map:
                    entity_map[nid] = node

        return InsightForgeResult(
            query=query,
            simulation_requirement=simulation_requirement,
            sub_queries=sub_queries,
            semantic_facts=all_facts,
            entity_insights=list(entity_map.values()),
            relationship_chains=relationship_chains,
            total_facts=len(all_facts),
            total_entities=len(entity_map),
            total_relationships=len(relationship_chains),
        )

    def _generate_sub_queries(
        self,
        query: str,
        simulation_requirement: str,
        report_context: str,
        max_sub_queries: int,
    ) -> List[str]:
        """Use LLM to generate diverse sub-queries for insight_forge."""
        try:
            llm = self._get_llm()
            prompt = (
                f"You are a research assistant. Given a main query and simulation context, "
                f"generate {max_sub_queries} diverse, specific sub-queries to retrieve comprehensive information.\n\n"
                f"Main Query: {query}\n"
                f"Simulation Requirement: {simulation_requirement}\n"
            )
            if report_context:
                prompt += f"Report Context: {report_context}\n"
            prompt += (
                f"\nReturn a JSON object with key \"sub_queries\" containing a list of "
                f"{max_sub_queries} sub-query strings. Each sub-query should explore a "
                f"different angle: entity relationships, behaviors, patterns, or topics."
            )

            result = llm.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
            )
            sub_queries = result.get("sub_queries", [])
            if isinstance(sub_queries, list):
                return [str(q) for q in sub_queries[:max_sub_queries]]
        except Exception as exc:
            logger.warning(
                "Mem0Provider: sub-query generation failed, falling back to empty list: %s", exc
            )
        return []

    def panorama_search(self, graph_id: str, query: str) -> PanoramaResult:
        """
        Full-scan search: get all memories and classify into active/historical facts.
        """
        try:
            memories = _mem0_get_all(self._client, graph_id, mode=self._mode)
        except Exception as exc:
            logger.error("Mem0Provider: panorama_search failed for graph_id=%s: %s", graph_id, exc)
            memories = []

        all_nodes: List[NodeInfo] = []
        all_edges: List[EdgeInfo] = []
        active_facts: List[str] = []
        historical_facts: List[str] = []

        for mem in memories:
            node = _memory_to_node(mem)
            all_nodes.append(node)

            content = mem.get("memory", "")
            if content:
                # Heuristic: memories without an updated_at or with recent creation
                # are treated as active; older ones or superseded as historical.
                updated_at = mem.get("updated_at", "")
                created_at = mem.get("created_at", "")
                # Treat all as active since Mem0 manages updates automatically
                active_facts.append(content)

            for rel in mem.get("relations", []) or []:
                edge = _relation_to_edge(rel, mem.get("id", ""))
                all_edges.append(edge)

        return PanoramaResult(
            query=query,
            all_nodes=all_nodes,
            all_edges=all_edges,
            active_facts=active_facts,
            historical_facts=historical_facts,
            total_nodes=len(all_nodes),
            total_edges=len(all_edges),
            active_count=len(active_facts),
            historical_count=len(historical_facts),
        )

    def quick_search(self, graph_id: str, query: str, limit: int = 5) -> SearchResult:
        """Delegate to search_graph with the given limit."""
        return self.search_graph(graph_id, query, limit=limit)

    def interview_agents(
        self,
        graph_id: str,
        interview_topic: str,
        interview_questions: List[str],
        num_agents: int = 3,
        agent_profiles: Optional[Dict] = None,
        simulation_id: Optional[str] = None,
    ) -> InterviewResult:
        """
        Return a placeholder InterviewResult.
        Agent interviews depend on SimulationRunner IPC and are not
        driven by the memory backend.
        """
        logger.info(
            "Mem0Provider: interview_agents called (placeholder) for graph_id=%s topic='%s'",
            graph_id,
            interview_topic,
        )
        return InterviewResult(
            interview_topic=interview_topic,
            interview_questions=interview_questions,
            selected_agents=[],
            interviews=[],
            selection_reasoning="interview_agents is not supported by Mem0Provider; use SimulationRunner IPC.",
            summary="Not available: Mem0Provider does not support direct agent interviews.",
            total_agents=0,
            interviewed_count=0,
        )

    def get_graph_statistics(self, graph_id: str) -> Dict[str, Any]:
        """Return counts of memories and relations."""
        try:
            memories = _mem0_get_all(self._client, graph_id, mode=self._mode)
        except Exception as exc:
            logger.error("Mem0Provider: get_graph_statistics failed: %s", exc)
            return {"graph_id": graph_id, "error": str(exc)}

        relation_count = sum(len(m.get("relations", []) or []) for m in memories)
        return {
            "graph_id": graph_id,
            "memory_count": len(memories),
            "relation_count": relation_count,
            "metadata": self._graphs.get(graph_id, {}),
        }

    def get_entity_summary(self, graph_id: str, entity_uuid: str) -> str:
        """Return a textual summary of an entity's relationships."""
        entity = self.get_entity_with_context(graph_id, entity_uuid)
        if not entity:
            return f"No information found for entity: {entity_uuid}"

        lines = [f"Entity: {entity.name}", f"Summary: {entity.summary}"]
        if entity.related_edges:
            lines.append("Relationships:")
            for edge in entity.related_edges[:10]:
                lines.append(f"  - {edge.get('fact', '')}")
        return "\n".join(lines)

    def get_all_nodes(self, graph_id: str) -> List[NodeInfo]:
        """Return all memory items as NodeInfo objects."""
        try:
            memories = _mem0_get_all(self._client, graph_id, mode=self._mode)
        except Exception as exc:
            logger.error("Mem0Provider: get_all_nodes failed: %s", exc)
            return []
        return [_memory_to_node(m) for m in memories]

    def get_all_edges(
        self, graph_id: str, include_temporal: bool = True
    ) -> List[EdgeInfo]:
        """Return all relation triples as EdgeInfo objects."""
        try:
            memories = _mem0_get_all(self._client, graph_id, mode=self._mode)
        except Exception as exc:
            logger.error("Mem0Provider: get_all_edges failed: %s", exc)
            return []

        edges: List[EdgeInfo] = []
        for mem in memories:
            for rel in mem.get("relations", []) or []:
                edges.append(_relation_to_edge(rel, mem.get("id", "")))
        return edges

    def get_simulation_context(self, graph_id: str, simulation_id: str) -> str:
        """Return a compact text context for a simulation."""
        graph_meta = self._graphs.get(graph_id, {})
        graph_name = graph_meta.get("name", graph_id)

        try:
            recent = _mem0_search(
                self._client,
                f"simulation {simulation_id}",
                graph_id,
                top_k=10,
                mode=self._mode,
            )
        except Exception:
            recent = []

        lines = [
            f"Graph: {graph_name} (id={graph_id})",
            f"Simulation: {simulation_id}",
        ]
        if recent:
            lines.append("Recent context:")
            for mem in recent[:5]:
                content = mem.get("memory", "")
                if content:
                    lines.append(f"  - {content}")
        return "\n".join(lines)

    def search_for_entity_context(
        self,
        graph_id: str,
        query: str,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """Search and return raw memory dicts for profile generation."""
        try:
            memories = _mem0_search(self._client, query, graph_id, top_k=limit, mode=self._mode)
        except Exception as exc:
            logger.error(
                "Mem0Provider: search_for_entity_context failed for graph_id=%s: %s",
                graph_id,
                exc,
            )
            return []

        results = []
        for mem in memories:
            results.append({
                "uuid": mem.get("id", ""),
                "name": mem.get("memory", "")[:80],
                "fact": mem.get("memory", ""),
                "score": mem.get("score", 0.0),
                "categories": mem.get("categories", []),
                "metadata": mem.get("metadata", {}),
                "relations": mem.get("relations", []),
            })
        return results
