"""
ZepProvider - wraps existing Zep services into the MemoryProvider interface.
Pure delegation: no behavior changes, just type conversion.
"""

from typing import Dict, Any, List, Optional

from .memory_provider import (
    MemoryProvider,
    EntityNode as ProviderEntityNode,
    FilteredEntities as ProviderFilteredEntities,
    SearchResult as ProviderSearchResult,
    NodeInfo as ProviderNodeInfo,
    EdgeInfo as ProviderEdgeInfo,
    InsightForgeResult as ProviderInsightForgeResult,
    PanoramaResult as ProviderPanoramaResult,
    AgentInterview as ProviderAgentInterview,
    InterviewResult as ProviderInterviewResult,
)
from .graph_builder import GraphBuilderService
from .zep_entity_reader import (
    ZepEntityReader,
    EntityNode as ZepEntityNode,
    FilteredEntities as ZepFilteredEntities,
)
from .zep_tools import (
    ZepToolsService,
    SearchResult as ZepSearchResult,
    NodeInfo as ZepNodeInfo,
    EdgeInfo as ZepEdgeInfo,
    InsightForgeResult as ZepInsightForgeResult,
    PanoramaResult as ZepPanoramaResult,
    InterviewResult as ZepInterviewResult,
    AgentInterview as ZepAgentInterview,
)
from .zep_graph_memory_updater import ZepGraphMemoryManager


# ============== Conversion helpers ==============

def _convert_entity_node(node: ZepEntityNode) -> ProviderEntityNode:
    """Convert a Zep-internal EntityNode to the provider-agnostic EntityNode."""
    return ProviderEntityNode(
        uuid=node.uuid,
        name=node.name,
        labels=node.labels,
        summary=node.summary,
        attributes=node.attributes,
        related_edges=node.related_edges,
        related_nodes=node.related_nodes,
    )


def _convert_filtered_entities(result: ZepFilteredEntities) -> ProviderFilteredEntities:
    """Convert Zep FilteredEntities to the provider-agnostic FilteredEntities."""
    return ProviderFilteredEntities(
        entities=[_convert_entity_node(e) for e in result.entities],
        entity_types=list(result.entity_types),
        total_count=result.total_count,
        filtered_count=result.filtered_count,
    )


def _convert_search_result(result: ZepSearchResult) -> ProviderSearchResult:
    """Convert a Zep SearchResult to the provider-agnostic SearchResult."""
    return ProviderSearchResult(
        facts=result.facts,
        edges=result.edges,
        nodes=result.nodes,
        query=result.query,
        total_count=result.total_count,
    )


def _convert_node_info(node: ZepNodeInfo) -> ProviderNodeInfo:
    """Convert a Zep NodeInfo to the provider-agnostic NodeInfo."""
    return ProviderNodeInfo(
        uuid=node.uuid,
        name=node.name,
        labels=node.labels,
        summary=node.summary,
        attributes=node.attributes,
    )


def _convert_edge_info(edge: ZepEdgeInfo) -> ProviderEdgeInfo:
    """Convert a Zep EdgeInfo to the provider-agnostic EdgeInfo."""
    return ProviderEdgeInfo(
        uuid=edge.uuid,
        name=edge.name,
        fact=edge.fact,
        source_node_uuid=edge.source_node_uuid,
        target_node_uuid=edge.target_node_uuid,
        source_node_name=edge.source_node_name,
        target_node_name=edge.target_node_name,
        created_at=edge.created_at,
        valid_at=edge.valid_at,
        invalid_at=edge.invalid_at,
        expired_at=edge.expired_at,
    )


def _convert_insight_forge_result(result: ZepInsightForgeResult) -> ProviderInsightForgeResult:
    """Convert a Zep InsightForgeResult to the provider-agnostic InsightForgeResult."""
    return ProviderInsightForgeResult(
        query=result.query,
        simulation_requirement=result.simulation_requirement,
        sub_queries=result.sub_queries,
        semantic_facts=result.semantic_facts,
        entity_insights=result.entity_insights,
        relationship_chains=result.relationship_chains,
        total_facts=result.total_facts,
        total_entities=result.total_entities,
        total_relationships=result.total_relationships,
    )


def _convert_panorama_result(result: ZepPanoramaResult) -> ProviderPanoramaResult:
    """Convert a Zep PanoramaResult to the provider-agnostic PanoramaResult."""
    return ProviderPanoramaResult(
        query=result.query,
        all_nodes=[_convert_node_info(n) for n in result.all_nodes],
        all_edges=[_convert_edge_info(e) for e in result.all_edges],
        active_facts=result.active_facts,
        historical_facts=result.historical_facts,
        total_nodes=result.total_nodes,
        total_edges=result.total_edges,
        active_count=result.active_count,
        historical_count=result.historical_count,
    )


def _convert_agent_interview(interview: ZepAgentInterview) -> ProviderAgentInterview:
    """Convert a Zep AgentInterview to the provider-agnostic AgentInterview.

    ZepAgentInterview has: agent_name, agent_role, agent_bio, question, response, key_quotes
    ProviderAgentInterview has: agent_name, agent_id, response, questions
    """
    return ProviderAgentInterview(
        agent_name=interview.agent_name,
        agent_id=getattr(interview, "agent_id", interview.agent_name),
        response=interview.response,
        questions=[interview.question] if hasattr(interview, "question") else [],
    )


def _convert_interview_result(result: ZepInterviewResult) -> ProviderInterviewResult:
    """Convert a Zep InterviewResult to the provider-agnostic InterviewResult."""
    return ProviderInterviewResult(
        interview_topic=result.interview_topic,
        interview_questions=result.interview_questions,
        selected_agents=result.selected_agents,
        interviews=[_convert_agent_interview(i) for i in result.interviews],
        selection_reasoning=result.selection_reasoning,
        summary=result.summary,
        total_agents=result.total_agents,
        interviewed_count=result.interviewed_count,
    )


# ============== ZepProvider ==============

class ZepProvider(MemoryProvider):
    """
    MemoryProvider implementation that delegates to the existing Zep services.

    All service instances are created lazily (on first use) and share the
    same api_key so callers can pass a per-request key if needed.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key
        self._graph_builder: Optional[GraphBuilderService] = None
        self._entity_reader: Optional[ZepEntityReader] = None
        self._tools: Optional[ZepToolsService] = None

    # --- lazy-init accessors ---

    @property
    def graph_builder(self) -> GraphBuilderService:
        if self._graph_builder is None:
            self._graph_builder = GraphBuilderService(api_key=self._api_key)
        return self._graph_builder

    @property
    def entity_reader(self) -> ZepEntityReader:
        if self._entity_reader is None:
            self._entity_reader = ZepEntityReader(api_key=self._api_key)
        return self._entity_reader

    @property
    def tools(self) -> ZepToolsService:
        if self._tools is None:
            self._tools = ZepToolsService(api_key=self._api_key)
        return self._tools

    # --- Graph Building ---

    def create_graph(self, name: str) -> str:
        return self.graph_builder.create_graph(name)

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> None:
        self.graph_builder.set_ontology(graph_id, ontology)

    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback=None,
    ) -> List[str]:
        return self.graph_builder.add_text_batches(
            graph_id, chunks, batch_size, progress_callback
        )

    def wait_for_processing(
        self,
        identifiers: List[str],
        progress_callback=None,
        timeout: int = 600,
    ) -> None:
        self.graph_builder._wait_for_episodes(
            identifiers, progress_callback, timeout
        )

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        return self.graph_builder.get_graph_data(graph_id)

    def delete_graph(self, graph_id: str) -> None:
        self.graph_builder.delete_graph(graph_id)

    # --- Entity Reading ---

    def filter_defined_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True,
    ) -> ProviderFilteredEntities:
        result = self.entity_reader.filter_defined_entities(
            graph_id, defined_entity_types, enrich_with_edges
        )
        return _convert_filtered_entities(result)

    def get_entity_with_context(
        self,
        graph_id: str,
        entity_uuid: str,
    ) -> Optional[ProviderEntityNode]:
        result = self.entity_reader.get_entity_with_context(graph_id, entity_uuid)
        if result is None:
            return None
        return _convert_entity_node(result)

    def get_entities_by_type(
        self,
        graph_id: str,
        entity_type: str,
    ) -> List[ProviderEntityNode]:
        results = self.entity_reader.get_entities_by_type(graph_id, entity_type)
        return [_convert_entity_node(e) for e in results]

    # --- Memory Updater (Simulation) ---

    def create_memory_updater(self, simulation_id: str, graph_id: str) -> None:
        ZepGraphMemoryManager.create_updater(simulation_id, graph_id)

    def stop_memory_updater(self, simulation_id: str) -> None:
        ZepGraphMemoryManager.stop_updater(simulation_id)

    def get_memory_updater(self, simulation_id: str):
        return ZepGraphMemoryManager.get_updater(simulation_id)

    def stop_all_memory_updaters(self) -> None:
        ZepGraphMemoryManager.stop_all()

    # --- Search & Analysis Tools ---

    def search_graph(
        self,
        graph_id: str,
        query: str,
        limit: int = 10,
    ) -> ProviderSearchResult:
        result = self.tools.search_graph(graph_id, query, limit)
        return _convert_search_result(result)

    def insight_forge(
        self,
        graph_id: str,
        query: str,
        simulation_requirement: str,
        report_context: str = "",
        max_sub_queries: int = 5,
    ) -> ProviderInsightForgeResult:
        result = self.tools.insight_forge(
            graph_id, query, simulation_requirement, report_context, max_sub_queries
        )
        return _convert_insight_forge_result(result)

    def panorama_search(
        self,
        graph_id: str,
        query: str,
    ) -> ProviderPanoramaResult:
        result = self.tools.panorama_search(graph_id, query)
        return _convert_panorama_result(result)

    def quick_search(
        self,
        graph_id: str,
        query: str,
        limit: int = 5,
    ) -> ProviderSearchResult:
        result = self.tools.quick_search(graph_id, query, limit)
        return _convert_search_result(result)

    def interview_agents(
        self,
        graph_id: str,
        interview_topic: str,
        interview_questions: List[str],
        num_agents: int = 3,
        agent_profiles: Optional[Dict] = None,
        simulation_id: Optional[str] = None,
    ) -> ProviderInterviewResult:
        # ZepToolsService uses simulation_id to access the simulation runner IPC.
        sid = simulation_id or graph_id
        result = self.tools.interview_agents(
            simulation_id=sid,
            interview_requirement=interview_topic,
            max_agents=num_agents,
            custom_questions=interview_questions if interview_questions else None,
        )
        return _convert_interview_result(result)

    def get_graph_statistics(self, graph_id: str) -> Dict[str, Any]:
        return self.tools.get_graph_statistics(graph_id)

    def get_entity_summary(self, graph_id: str, entity_uuid: str) -> str:
        result = self.tools.get_entity_summary(graph_id, entity_uuid)
        # ZepToolsService returns Dict; ABC contract is str
        if isinstance(result, dict):
            import json
            return json.dumps(result, ensure_ascii=False, indent=2)
        return str(result)

    def get_all_nodes(self, graph_id: str) -> List[ProviderNodeInfo]:
        results = self.tools.get_all_nodes(graph_id)
        return [_convert_node_info(n) for n in results]

    def get_all_edges(
        self,
        graph_id: str,
        include_temporal: bool = True,
    ) -> List[ProviderEdgeInfo]:
        results = self.tools.get_all_edges(graph_id, include_temporal)
        return [_convert_edge_info(e) for e in results]

    def get_simulation_context(self, graph_id: str, simulation_id: str) -> str:
        return self.tools.get_simulation_context(graph_id, simulation_id)

    # --- Profile Generation ---

    def search_for_entity_context(
        self,
        graph_id: str,
        query: str,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        result = self.tools.search_graph(graph_id, query, limit)
        return result.nodes
