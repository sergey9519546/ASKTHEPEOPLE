"""
Graph Building Service
Endpoint 2: Build Standalone Graph using Zep API
"""

import hashlib
import re
import time
import uuid
from collections.abc import Sequence
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from zep_cloud.client import Zep
from zep_cloud import EpisodeData, EntityEdgeSourceTarget

from ..config import Config
from ..utils.task_retry import retry_transient_operation
from ..utils.zep_paging import fetch_all_nodes, fetch_all_edges
from .text_processor import TextProcessor

@dataclass
class GraphInfo:
    """Graph Information"""
    graph_id: str
    node_count: int
    edge_count: int
    entity_types: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "entity_types": self.entity_types,
        }


class GraphBuildProviderError(RuntimeError):
    """Stable provider failure annotated with whether a whole-task retry is safe."""

    def __init__(self, code: str, *, graph_id: str, retry_safe: bool):
        super().__init__(code)
        self.graph_id = graph_id
        self.retry_safe = retry_safe


def _graph_owner_marker(graph_id: str) -> str:
    """Return the exact non-secret ownership marker for a server graph ID."""
    digest = hashlib.sha256(f"source-graph:{graph_id}".encode()).hexdigest()
    return f"source_graph_owner:{digest}"


def _is_uuid(value: object) -> bool:
    """Accept only provider acknowledgements with a real UUID identifier."""
    if not isinstance(value, str):
        return False
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def _to_pascal_case(value: str) -> str:
    """Normalize separators without corrupting an existing PascalCase name."""
    normalized = re.sub(r"[^a-zA-Z0-9\s_]", "", value)
    parts = [part for part in normalized.replace(" ", "_").split("_") if part]
    return "".join(part[:1].upper() + part[1:] for part in parts)


class GraphBuilderService:
    """Build a Zep-derived source graph without owning background execution."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.ZEP_API_KEY
        if not self.api_key:
            raise ValueError("ZEP_API_KEY not configured")

        self.client = Zep(api_key=self.api_key)

    def build_graph(
        self,
        *,
        graph_id: str,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str,
        chunk_size: int,
        chunk_overlap: int,
        batch_size: int = 3,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[str, Any]:
        """Build a source graph synchronously for a Celery-owned worker.

        The caller owns input loading, persistence, and task lifecycle.  This
        operation only performs the provider sequence and returns serializable
        derived graph information; it never starts a local worker thread.
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError("extracted source text is required")
        if not isinstance(ontology, dict):
            raise ValueError("ontology must be a mapping")

        def report(progress: int, message: str) -> None:
            if progress_callback:
                progress_callback(progress, message)

        try:
            # Creation and ontology assignment are keyed by the caller's stable
            # graph ID, so replaying this phase cannot create a second graph.
            self.create_graph(graph_id, graph_name)
            report(10, "Graph created")

            self.set_ontology(graph_id, ontology)
            report(15, "Ontology configured")
        except GraphBuildProviderError:
            raise
        except Exception as exc:
            raise GraphBuildProviderError(
                "graph_create_phase_failed",
                graph_id=graph_id,
                retry_safe=True,
            ) from exc

        chunks = TextProcessor.split_text(text, chunk_size, chunk_overlap)
        total_chunks = len(chunks)
        report(20, f"Prepared {total_chunks} source chunks")
        if not chunks:
            raise GraphBuildProviderError(
                "graph_episode_submission_unconfirmed",
                graph_id=graph_id,
                retry_safe=False,
            )

        try:
            # Episode submission is not idempotent. Any failure from this point
            # is ambiguous and must terminate instead of replaying the build.
            episode_uuids = self.add_text_batches(
                graph_id,
                chunks,
                batch_size,
                lambda message, fraction: report(20 + int(fraction * 40), message),
            )
            report(60, "Waiting for graph processing")
            self._wait_for_episodes(
                episode_uuids,
                lambda message, fraction: report(60 + int(fraction * 30), message),
            )

            report(90, "Reading graph information")
            graph_info = self._get_graph_info(graph_id)
        except GraphBuildProviderError:
            raise
        except Exception as exc:
            raise GraphBuildProviderError(
                "graph_post_mutation_failed",
                graph_id=graph_id,
                retry_safe=False,
            ) from exc
        report(100, "Graph build complete")
        return {
            "success": True,
            "graph_id": graph_id,
            "graph_info": graph_info.to_dict(),
            "chunks_processed": total_chunks,
        }
    
    def create_graph(self, graph_id: str, name: str) -> str:
        """Create Zep graph (public method)"""
        marker = _graph_owner_marker(graph_id)
        try:
            self.client.graph.create(
                graph_id=graph_id,
                name=name,
                description=marker,
            )
        except Exception as exc:
            if getattr(exc, "status_code", None) != 409:
                raise

            # A conflict is reusable only when it is provably the empty graph
            # created by an earlier delivery of this exact task identity.
            try:
                graph = retry_transient_operation(
                    lambda: self.client.graph.get(graph_id=graph_id),
                    max_attempts=3,
                )
                description = (
                    graph.get("description")
                    if isinstance(graph, dict)
                    else getattr(graph, "description", None)
                )
                if description != marker:
                    raise RuntimeError("unsafe graph create conflict")
                episode_response = retry_transient_operation(
                    lambda: self.client.graph.episode.get_by_graph_id(
                        graph_id=graph_id,
                        lastn=1,
                    ),
                    max_attempts=3,
                )
                episodes = getattr(episode_response, "episodes", episode_response)
                is_empty_sequence = (
                    isinstance(episodes, Sequence)
                    and not isinstance(episodes, (str, bytes))
                    and len(episodes) == 0
                )
                if not is_empty_sequence:
                    raise RuntimeError("unsafe graph create conflict")
            except Exception as verify_exc:
                raise GraphBuildProviderError(
                    "graph_create_conflict_unsafe",
                    graph_id=graph_id,
                    retry_safe=False,
                ) from verify_exc
        
        return graph_id
    
    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        """Set graph ontology (public method)"""
        import warnings
        from typing import Optional
        from pydantic import Field
        from zep_cloud.external_clients.ontology import EntityModel, EntityText, EdgeModel
        
        # Suppress Pydantic v2 warnings about Field(default=None)
        # This is usage required by Zep SDK; warnings come from dynamic class creation and can be safely ignored
        warnings.filterwarnings('ignore', category=UserWarning, module='pydantic')
        
        # Zep reserved names, cannot be used as attribute names
        RESERVED_NAMES = {'uuid', 'name', 'group_id', 'name_embedding', 'summary', 'created_at'}
        
        def safe_attr_name(attr_name: str) -> str:
            """Convert reserved names to safe names"""
            if attr_name.lower() in RESERVED_NAMES:
                return f"entity_{attr_name}"
            return attr_name
        
        # Dynamically create entity types
        entity_types = {}
        for entity_def in ontology.get("entity_types", []):
            name = _to_pascal_case(entity_def["name"])
            description = entity_def.get("description", f"A {name} entity.")
            
            # Create attribute dictionary and type annotations (required by Pydantic v2)
            attrs = {"__doc__": description}
            annotations = {}
            
            for attr_def in entity_def.get("attributes", []):
                attr_name = safe_attr_name(attr_def["name"])  # Use safe name
                attr_desc = attr_def.get("description", attr_name)
                # Zep API requires Field description, which is mandatory
                attrs[attr_name] = Field(description=attr_desc, default=None)
                annotations[attr_name] = Optional[EntityText]  # Type annotation
            
            attrs["__annotations__"] = annotations
            
            # Dynamically create class
            entity_class = type(name, (EntityModel,), attrs)
            entity_class.__doc__ = description
            entity_types[name] = entity_class
        
        # Dynamically create edge types
        edge_definitions = {}
        for edge_def in ontology.get("edge_types", []):
            name = _to_pascal_case(edge_def["name"])
            description = edge_def.get("description", f"A {name} relationship.")
            
            # Create attribute dictionary and type annotations
            attrs = {"__doc__": description}
            annotations = {}
            
            for attr_def in edge_def.get("attributes", []):
                attr_name = safe_attr_name(attr_def["name"])  # Use safe name
                attr_desc = attr_def.get("description", attr_name)
                # Zep API requires Field description, which is mandatory
                attrs[attr_name] = Field(description=attr_desc, default=None)
                annotations[attr_name] = Optional[str]  # Edge attributes use str type
            
            attrs["__annotations__"] = annotations
            
            # Dynamically create class
            class_name = name

            edge_class = type(class_name, (EdgeModel,), attrs)
            edge_class.__doc__ = description
            
            # Build source_targets
            source_targets = []
            for st in edge_def.get("source_targets", []):
                source_targets.append(
                    EntityEdgeSourceTarget(
                        source=_to_pascal_case(st.get("source", "Entity")),
                        target=_to_pascal_case(st.get("target", "Entity"))
                    )
                )
            
            if source_targets:
                edge_definitions[name] = (edge_class, source_targets)
        
        # Call Zep API to set ontology
        if entity_types or edge_definitions:
            self.client.graph.set_ontology(
                graph_ids=[graph_id],
                entities=entity_types if entity_types else None,
                edges=edge_definitions if edge_definitions else None,
            )
    
    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        """Add text to graph in batches, return list of all episode uuids"""
        episode_uuids = []
        total_chunks = len(chunks)
        if total_chunks == 0:
            raise GraphBuildProviderError(
                "graph_episode_submission_unconfirmed",
                graph_id=graph_id,
                retry_safe=False,
            )
        
        for i in range(0, total_chunks, batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_chunks + batch_size - 1) // batch_size
            
            if progress_callback:
                progress = (i + len(batch_chunks)) / total_chunks
                progress_callback(
                    f"Sending batch {batch_num}/{total_batches} ({len(batch_chunks)} chunks)...",
                    progress
                )
            
            # Build episode data
            episodes = [
                EpisodeData(data=chunk, type="text")
                for chunk in batch_chunks
            ]
            
            # Send to Zep
            try:
                batch_result = self.client.graph.add_batch(
                    graph_id=graph_id,
                    episodes=episodes
                )
                
                if (
                    not isinstance(batch_result, Sequence)
                    or isinstance(batch_result, (str, bytes))
                    or not batch_result
                ):
                    raise GraphBuildProviderError(
                        "graph_episode_submission_unconfirmed",
                        graph_id=graph_id,
                        retry_safe=False,
                    )

                batch_uuids = [
                    getattr(ep, "uuid_", None) or getattr(ep, "uuid", None)
                    for ep in batch_result
                ]
                if len(batch_uuids) != len(batch_chunks) or any(
                    not _is_uuid(ep_uuid) for ep_uuid in batch_uuids
                ):
                    raise GraphBuildProviderError(
                        "graph_episode_submission_unconfirmed",
                        graph_id=graph_id,
                        retry_safe=False,
                    )
                episode_uuids.extend(batch_uuids)
                
                # Avoid sending requests too fast
                time.sleep(1)
                
            except Exception:
                if progress_callback:
                    progress_callback(f"Batch {batch_num} could not be submitted", 0)
                raise
        
        return episode_uuids
    
    def _wait_for_episodes(
        self,
        episode_uuids: List[str],
        progress_callback: Optional[Callable] = None,
        timeout: int = 600
    ):
        """Wait for all processing to complete (by querying the processed status of each episode)"""
        if not episode_uuids:
            if progress_callback:
                progress_callback("No need to wait (no episode)", 1.0)
            return
        
        start_time = time.time()
        pending_episodes = set(episode_uuids)
        completed_count = 0
        total_episodes = len(episode_uuids)
        
        if progress_callback:
            progress_callback(f"Starting to wait for {total_episodes} text chunks to process...", 0)
        
        while pending_episodes:
            if time.time() - start_time >= timeout:
                if progress_callback:
                    progress_callback(
                        f"Some text blocks timed out, completed {completed_count}/{total_episodes}",
                        completed_count / total_episodes
                    )
                raise RuntimeError("graph_processing_timeout")
            
            # Check processing status of each episode
            for ep_uuid in list(pending_episodes):
                try:
                    episode = retry_transient_operation(
                        lambda: self.client.graph.episode.get(uuid_=ep_uuid),
                        max_attempts=3,
                    )
                    is_processed = getattr(episode, 'processed', False)
                    
                    if is_processed:
                        pending_episodes.remove(ep_uuid)
                        completed_count += 1
                        
                except Exception as exc:
                    raise GraphBuildProviderError(
                        "graph_processing_failed",
                        graph_id="",
                        retry_safe=False,
                    ) from exc

            elapsed = int(time.time() - start_time)
            if progress_callback:
                progress_callback(
                    f"Zep processing... {completed_count}/{total_episodes} Complete, {len(pending_episodes)} pending ({elapsed}s)",
                    completed_count / total_episodes if total_episodes > 0 else 0
                )
            
            if pending_episodes:
                time.sleep(3)  # Check every 3 seconds
        
        if progress_callback:
            progress_callback(f"Processing complete: {completed_count}/{total_episodes}", 1.0)
    
    def _get_graph_info(self, graph_id: str) -> GraphInfo:
        """Get Graph Information"""
        # Get nodes (paged)
        nodes = fetch_all_nodes(self.client, graph_id)

        # Get edges (paged)
        edges = fetch_all_edges(self.client, graph_id)

        # Count entity types
        entity_types = set()
        for node in nodes:
            if node.labels:
                for label in node.labels:
                    if label not in ["Entity", "Node"]:
                        entity_types.add(label)

        return GraphInfo(
            graph_id=graph_id,
            node_count=len(nodes),
            edge_count=len(edges),
            entity_types=list(entity_types)
        )
    
    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """
        Get full graph data (including details)
        
        Args:
            graph_id: Graph ID
            
        Returns:
            Dictionary containing nodes and edges, including time info, attributes, and other detailed data
        """
        nodes = fetch_all_nodes(self.client, graph_id)
        edges = fetch_all_edges(self.client, graph_id)

        # Create node mapping to get node names
        node_map = {}
        for node in nodes:
            node_map[node.uuid_] = node.name or ""
        
        nodes_data = []
        for node in nodes:
            # Get creation time
            created_at = getattr(node, 'created_at', None)
            if created_at:
                created_at = str(created_at)
            
            nodes_data.append({
                "uuid": node.uuid_,
                "name": node.name,
                "labels": node.labels or [],
                "summary": node.summary or "",
                "attributes": node.attributes or {},
                "created_at": created_at,
            })
        
        edges_data = []
        for edge in edges:
            # Get time info
            created_at = getattr(edge, 'created_at', None)
            valid_at = getattr(edge, 'valid_at', None)
            invalid_at = getattr(edge, 'invalid_at', None)
            expired_at = getattr(edge, 'expired_at', None)
            
            # Get episodes
            episodes = getattr(edge, 'episodes', None) or getattr(edge, 'episode_ids', None)
            if episodes and not isinstance(episodes, list):
                episodes = [str(episodes)]
            elif episodes:
                episodes = [str(e) for e in episodes]
            
            # Get fact_type
            fact_type = getattr(edge, 'fact_type', None) or edge.name or ""
            
            edges_data.append({
                "uuid": edge.uuid_,
                "name": edge.name or "",
                "fact": edge.fact or "",
                "fact_type": fact_type,
                "source_node_uuid": edge.source_node_uuid,
                "target_node_uuid": edge.target_node_uuid,
                "source_node_name": node_map.get(edge.source_node_uuid, ""),
                "target_node_name": node_map.get(edge.target_node_uuid, ""),
                "attributes": edge.attributes or {},
                "created_at": str(created_at) if created_at else None,
                "valid_at": str(valid_at) if valid_at else None,
                "invalid_at": str(invalid_at) if invalid_at else None,
                "expired_at": str(expired_at) if expired_at else None,
                "episodes": episodes or [],
            })
        
        return {
            "graph_id": graph_id,
            "nodes": nodes_data,
            "edges": edges_data,
            "node_count": len(nodes_data),
            "edge_count": len(edges_data),
        }
    
    def delete_graph(self, graph_id: str):
        """Delete graph"""
        self.client.graph.delete(graph_id=graph_id)

