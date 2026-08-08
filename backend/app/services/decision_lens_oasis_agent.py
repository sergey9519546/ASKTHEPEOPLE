"""Application-owned OASIS agents for reviewed functional decision lenses."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from camel.prompts import TextPrompt
from oasis.social_agent.agent import SocialAgent
from oasis.social_agent.agent_graph import AgentGraph
from oasis.social_platform.config import UserInfo

from .decision_lens_runtime_adapter import (
    DecisionLensRuntimeAdapterV1,
    render_semantic_prompt,
)

DecisionLensPlatform = Literal["twitter", "reddit"]
RUNTIME_ADAPTER_FILENAME = "decision_lens_runtime.v1.json"
_RUNTIME_KEYS = {
    "schema_version",
    "source_artifact_sha256",
    "source_review_sha256",
    "adapters",
}
_SEMANTIC_PROMPT_TEMPLATE = TextPrompt("{semantic_prompt}")


class DecisionLensOasisAgentError(ValueError):
    """Stable fail-closed error without prompt or profile disclosure."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class DecisionLensSocialAgent(SocialAgent):
    """Pinned OASIS agent whose system instruction is the reviewed lens."""

    def __init__(
        self,
        *,
        adapter: DecisionLensRuntimeAdapterV1,
        platform: DecisionLensPlatform,
        model: Any,
        available_actions: Sequence[Any],
        channel: Any | None = None,
        agent_graph: AgentGraph | None = None,
    ) -> None:
        if platform not in {"twitter", "reddit"}:
            raise DecisionLensOasisAgentError("decision_lens_platform_invalid")
        if not available_actions:
            raise DecisionLensOasisAgentError("decision_lens_actions_required")

        validated = DecisionLensRuntimeAdapterV1.model_validate(
            adapter.model_dump(mode="python")
        )
        semantic_prompt = render_semantic_prompt(validated)
        user_info = UserInfo(
            user_name=validated.platform_username,
            name=validated.platform_name,
            description=validated.platform_description,
            profile={"semantic_prompt": semantic_prompt},
            recsys_type=platform,
        )
        super().__init__(
            agent_id=validated.agent_id,
            user_info=user_info,
            user_info_template=_SEMANTIC_PROMPT_TEMPLATE,
            channel=channel,
            model=model,
            agent_graph=agent_graph,
            available_actions=list(available_actions),
        )
        self.runtime_adapter = validated
        if (
            self.system_message is None
            or self.system_message.role_name != "system"
            or self.system_message.content != semantic_prompt
        ):
            raise DecisionLensOasisAgentError(
                "decision_lens_system_instruction_invalid"
            )


async def generate_decision_lens_agent_graph(
    *,
    adapters: Sequence[DecisionLensRuntimeAdapterV1],
    platform: DecisionLensPlatform,
    model: Any,
    available_actions: Sequence[Any],
    channel: Any | None = None,
) -> AgentGraph:
    """Build a fresh pinned-OASIS graph without legacy persona generators."""

    validated = _validate_adapter_sequence(adapters)
    if not available_actions:
        raise DecisionLensOasisAgentError("decision_lens_actions_required")
    graph = AgentGraph()
    for adapter in validated:
        graph.add_agent(
            DecisionLensSocialAgent(
                adapter=adapter,
                platform=platform,
                model=model,
                available_actions=available_actions,
                channel=channel,
                agent_graph=graph,
            )
        )
    return graph


def load_decision_lens_runtime_adapters(
    simulation_dir: str | Path,
) -> tuple[DecisionLensRuntimeAdapterV1, ...]:
    """Load only the reviewed runtime artifact accepted by the new boundary."""

    runtime_path = Path(simulation_dir) / RUNTIME_ADAPTER_FILENAME
    if not runtime_path.is_file():
        raise DecisionLensOasisAgentError("decision_lens_runtime_required")
    try:
        payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or set(payload) != _RUNTIME_KEYS:
            raise DecisionLensOasisAgentError("decision_lens_runtime_invalid")
        if payload["schema_version"] != "decision-lens-runtime/v1":
            raise DecisionLensOasisAgentError("decision_lens_runtime_invalid")
        raw_adapters = payload["adapters"]
        if not isinstance(raw_adapters, list):
            raise DecisionLensOasisAgentError("decision_lens_runtime_invalid")
        adapters = _validate_adapter_sequence(raw_adapters)
        if any(
            adapter.source_artifact_sha256
            != payload["source_artifact_sha256"]
            or adapter.source_review_sha256 != payload["source_review_sha256"]
            for adapter in adapters
        ):
            raise DecisionLensOasisAgentError("decision_lens_runtime_invalid")
        return adapters
    except DecisionLensOasisAgentError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise DecisionLensOasisAgentError(
            "decision_lens_runtime_invalid"
        ) from exc


def _validate_adapter_sequence(
    adapters: Sequence[DecisionLensRuntimeAdapterV1] | Sequence[object],
) -> tuple[DecisionLensRuntimeAdapterV1, ...]:
    try:
        validated = tuple(
            DecisionLensRuntimeAdapterV1.model_validate(adapter)
            for adapter in adapters
        )
    except (TypeError, ValueError) as exc:
        raise DecisionLensOasisAgentError(
            "decision_lens_runtime_invalid"
        ) from exc
    if not validated:
        raise DecisionLensOasisAgentError("decision_lens_runtime_incomplete")
    if tuple(adapter.agent_id for adapter in validated) != tuple(
        range(len(validated))
    ):
        raise DecisionLensOasisAgentError("decision_lens_adapter_ids_invalid")
    return validated


__all__ = [
    "DecisionLensOasisAgentError",
    "DecisionLensSocialAgent",
    "generate_decision_lens_agent_graph",
    "load_decision_lens_runtime_adapters",
]
