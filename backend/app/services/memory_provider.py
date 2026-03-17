"""
Memory Provider抽象接口
定义MiroFish记忆后端的统一接口，支持Zep和Mem0等多种后端
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


# ============== 共享数据类 ==============

@dataclass
class EntityNode:
    """实体节点数据结构"""
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
            "related_edges": self.related_edges,
            "related_nodes": self.related_nodes,
        }

    def get_entity_type(self) -> Optional[str]:
        """获取实体类型（排除默认的Entity标签）"""
        for label in self.labels:
            if label not in ["Entity", "Node"]:
                return label
        return None


@dataclass
class FilteredEntities:
    """过滤后的实体集合"""
    entities: List[EntityNode]
    entity_types: List[str]
    total_count: int
    filtered_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "entity_types": self.entity_types,
            "total_count": self.total_count,
            "filtered_count": self.filtered_count,
        }


@dataclass
class SearchResult:
    """搜索结果"""
    facts: List[str]
    edges: List[Dict[str, Any]]
    nodes: List[Dict[str, Any]]
    query: str
    total_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": self.facts,
            "edges": self.edges,
            "nodes": self.nodes,
            "query": self.query,
            "total_count": self.total_count,
        }

    def to_text(self) -> str:
        return f"Query: {self.query}\nFacts ({self.total_count}):\n" + "\n".join(
            f"- {f}" for f in self.facts
        )


@dataclass
class NodeInfo:
    """节点信息"""
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
        }


@dataclass
class EdgeInfo:
    """边信息"""
    uuid: str
    name: str
    fact: str
    source_node_uuid: str
    target_node_uuid: str
    source_node_name: Optional[str] = None
    target_node_name: Optional[str] = None
    created_at: Optional[str] = None
    valid_at: Optional[str] = None
    invalid_at: Optional[str] = None
    expired_at: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        return self.expired_at is not None

    @property
    def is_invalid(self) -> bool:
        return self.invalid_at is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "fact": self.fact,
            "source_node_uuid": self.source_node_uuid,
            "target_node_uuid": self.target_node_uuid,
            "source_node_name": self.source_node_name,
            "target_node_name": self.target_node_name,
            "created_at": self.created_at,
            "valid_at": self.valid_at,
            "invalid_at": self.invalid_at,
            "expired_at": self.expired_at,
        }


@dataclass
class InsightForgeResult:
    """深度洞察搜索结果"""
    query: str
    simulation_requirement: str
    sub_queries: List[str]
    semantic_facts: List[str]
    entity_insights: List[Dict[str, Any]]
    relationship_chains: List[str]
    total_facts: int
    total_entities: int
    total_relationships: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "simulation_requirement": self.simulation_requirement,
            "sub_queries": self.sub_queries,
            "semantic_facts": self.semantic_facts,
            "entity_insights": self.entity_insights,
            "relationship_chains": self.relationship_chains,
            "total_facts": self.total_facts,
            "total_entities": self.total_entities,
            "total_relationships": self.total_relationships,
        }

    def to_text(self) -> str:
        text = f"Query: {self.query}\nSub-queries: {self.sub_queries}\n"
        text += f"Semantic Facts ({self.total_facts}):\n"
        text += "\n".join(f"- {f}" for f in self.semantic_facts)
        if self.relationship_chains:
            text += f"\n\nRelationship Chains ({self.total_relationships}):\n"
            text += "\n".join(f"- {r}" for r in self.relationship_chains)
        return text


@dataclass
class PanoramaResult:
    """全景搜索结果"""
    query: str
    all_nodes: List[NodeInfo]
    all_edges: List[EdgeInfo]
    active_facts: List[str]
    historical_facts: List[str]
    total_nodes: int
    total_edges: int
    active_count: int
    historical_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "all_nodes": [n.to_dict() for n in self.all_nodes],
            "all_edges": [e.to_dict() for e in self.all_edges],
            "active_facts": self.active_facts,
            "historical_facts": self.historical_facts,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "active_count": self.active_count,
            "historical_count": self.historical_count,
        }

    def to_text(self) -> str:
        text = f"Active facts ({self.active_count}):\n"
        text += "\n".join(f"- {f}" for f in self.active_facts)
        if self.historical_facts:
            text += f"\n\nHistorical facts ({self.historical_count}):\n"
            text += "\n".join(f"- {f}" for f in self.historical_facts)
        return text


@dataclass
class AgentInterview:
    """单个Agent访谈结果"""
    agent_name: str
    agent_id: str
    response: str
    questions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "agent_id": self.agent_id,
            "response": self.response,
            "questions": self.questions,
        }


@dataclass
class InterviewResult:
    """访谈结果"""
    interview_topic: str
    interview_questions: List[str]
    selected_agents: List[Dict[str, Any]]
    interviews: List[AgentInterview]
    selection_reasoning: str
    summary: str
    total_agents: int
    interviewed_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interview_topic": self.interview_topic,
            "interview_questions": self.interview_questions,
            "selected_agents": self.selected_agents,
            "interviews": [i.to_dict() for i in self.interviews],
            "selection_reasoning": self.selection_reasoning,
            "summary": self.summary,
            "total_agents": self.total_agents,
            "interviewed_count": self.interviewed_count,
        }

    def to_text(self) -> str:
        text = f"Topic: {self.interview_topic}\nSummary: {self.summary}\n"
        for iv in self.interviews:
            text += f"\n{iv.agent_name}: {iv.response[:200]}"
        return text


# ============== 抽象接口 ==============

class MemoryProvider(ABC):
    """
    MiroFish记忆后端抽象接口
    所有记忆提供者（Zep、Mem0等）必须实现此接口
    """

    # --- Graph Building ---

    @abstractmethod
    def create_graph(self, name: str) -> str:
        """创建新图谱，返回graph_id"""

    @abstractmethod
    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> None:
        """设置实体/关系类型定义"""

    @abstractmethod
    def add_text_batches(self, graph_id: str, chunks: List[str],
                         batch_size: int = 3,
                         progress_callback=None) -> List[str]:
        """批量添加文本块，返回标识符列表"""

    @abstractmethod
    def wait_for_processing(self, identifiers: List[str],
                            progress_callback=None,
                            timeout: int = 600) -> None:
        """等待数据处理完成（某些后端可能无需等待）"""

    @abstractmethod
    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """获取图谱完整数据: {graph_id, nodes, edges, node_count, edge_count}"""

    @abstractmethod
    def delete_graph(self, graph_id: str) -> None:
        """删除图谱及所有数据"""

    # --- Entity Reading ---

    @abstractmethod
    def filter_defined_entities(self, graph_id: str,
                                 defined_entity_types: Optional[List[str]] = None,
                                 enrich_with_edges: bool = True) -> FilteredEntities:
        """按类型过滤实体"""

    @abstractmethod
    def get_entity_with_context(self, graph_id: str,
                                 entity_uuid: str) -> Optional[EntityNode]:
        """获取实体及其关联的边和节点"""

    @abstractmethod
    def get_entities_by_type(self, graph_id: str,
                              entity_type: str) -> List[EntityNode]:
        """按类型获取实体列表"""

    # --- Memory Updater (Simulation) ---

    @abstractmethod
    def create_memory_updater(self, simulation_id: str,
                               graph_id: str) -> None:
        """为模拟创建并启动记忆更新器"""

    @abstractmethod
    def stop_memory_updater(self, simulation_id: str) -> None:
        """停止记忆更新器并flush剩余数据"""

    @abstractmethod
    def get_memory_updater(self, simulation_id: str):
        """获取记忆更新器实例"""

    @abstractmethod
    def stop_all_memory_updaters(self) -> None:
        """停止所有记忆更新器"""

    # --- Search & Analysis Tools ---

    @abstractmethod
    def search_graph(self, graph_id: str, query: str,
                      limit: int = 10) -> SearchResult:
        """语义搜索图谱"""

    @abstractmethod
    def insight_forge(self, graph_id: str, query: str,
                       simulation_requirement: str,
                       report_context: str = "",
                       max_sub_queries: int = 5) -> InsightForgeResult:
        """深度多维搜索"""

    @abstractmethod
    def panorama_search(self, graph_id: str,
                         query: str) -> PanoramaResult:
        """全景搜索"""

    @abstractmethod
    def quick_search(self, graph_id: str, query: str,
                      limit: int = 5) -> SearchResult:
        """快速关键词搜索"""

    @abstractmethod
    def interview_agents(self, graph_id: str,
                          interview_topic: str,
                          interview_questions: List[str],
                          num_agents: int = 3,
                          agent_profiles: Optional[Dict] = None,
                          simulation_id: Optional[str] = None) -> InterviewResult:
        """访谈模拟Agent。simulation_id用于Zep后端访问模拟运行器。"""

    @abstractmethod
    def get_graph_statistics(self, graph_id: str) -> Dict[str, Any]:
        """获取图谱统计信息"""

    @abstractmethod
    def get_entity_summary(self, graph_id: str,
                            entity_uuid: str) -> str:
        """获取实体关系摘要"""

    @abstractmethod
    def get_all_nodes(self, graph_id: str) -> List[NodeInfo]:
        """获取所有节点"""

    @abstractmethod
    def get_all_edges(self, graph_id: str,
                       include_temporal: bool = True) -> List[EdgeInfo]:
        """获取所有边"""

    @abstractmethod
    def get_simulation_context(self, graph_id: str,
                                simulation_id: str) -> str:
        """获取模拟上下文信息"""

    # --- Profile Generation ---

    @abstractmethod
    def search_for_entity_context(self, graph_id: str, query: str,
                                   limit: int = 30) -> List[Dict[str, Any]]:
        """搜索实体上下文（用于Profile生成丰富信息）"""
