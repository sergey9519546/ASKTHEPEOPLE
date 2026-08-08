"""Application-owned OASIS agents preserve reviewed functional prompts."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from camel.models import StubModel
from camel.types import ModelType
from oasis import ActionType

from tests.test_decision_lens_runtime_adapter import approved_pair


def _stub_model() -> StubModel:
    return StubModel(ModelType.STUB)


def test_runtime_adapters_use_pinned_oasis_zero_based_ids(tmp_path) -> None:
    from app.services.decision_lens_runtime_adapter import build_runtime_adapters

    artifact, review = approved_pair(tmp_path)
    adapters = build_runtime_adapters(artifact, review)

    assert [adapter.agent_id for adapter in adapters] == list(
        range(len(adapters))
    )
    assert adapters[0].platform_username == "decision_lens_01"


def test_local_agent_uses_exact_semantic_prompt_not_transport_labels(
    tmp_path,
) -> None:
    from app.services.decision_lens_oasis_agent import DecisionLensSocialAgent
    from app.services.decision_lens_runtime_adapter import (
        build_runtime_adapters,
        render_semantic_prompt,
    )

    artifact, review = approved_pair(tmp_path)
    adapter = build_runtime_adapters(artifact, review)[0]
    relabeled = adapter.model_copy(
        update={
            "platform_name": "Changed transport label",
            "platform_username": "decision_lens_99",
        }
    )

    original = DecisionLensSocialAgent(
        adapter=adapter,
        platform="twitter",
        model=_stub_model(),
        available_actions=[ActionType.CREATE_POST, ActionType.DO_NOTHING],
    )
    changed = DecisionLensSocialAgent(
        adapter=relabeled,
        platform="twitter",
        model=_stub_model(),
        available_actions=[ActionType.CREATE_POST, ActionType.DO_NOTHING],
    )

    assert original.system_message.content == render_semantic_prompt(adapter)
    context, _ = original.memory.get_context()
    assert context[0] == {
        "role": "system",
        "content": render_semantic_prompt(adapter),
    }
    assert changed.system_message.content == original.system_message.content
    assert changed.user_info.name == "Changed transport label"
    assert changed.user_info.user_name == "decision_lens_99"


@pytest.mark.asyncio
async def test_round_context_overlay_is_used_once_without_mutating_system_prompt(
    tmp_path,
) -> None:
    from app.services.decision_lens_oasis_agent import DecisionLensSocialAgent
    from app.services.decision_lens_runtime_adapter import build_runtime_adapters

    artifact, review = approved_pair(tmp_path)
    adapter = build_runtime_adapters(artifact, review)[0]
    agent = DecisionLensSocialAgent(
        adapter=adapter,
        platform="twitter",
        model=_stub_model(),
        available_actions=[ActionType.CREATE_POST, ActionType.DO_NOTHING],
    )
    original_system_prompt = agent.system_message.content
    agent.env.to_text_prompt = AsyncMock(return_value="Current platform timeline.")
    response = MagicMock()
    response.info = {"tool_calls": []}
    observed_contexts: list[list[str]] = []

    async def _capture_context(_message):
        context, _ = agent.memory.get_context()
        observed_contexts.append([message["content"] for message in context])
        return response

    agent.astep = AsyncMock(side_effect=_capture_context)

    agent.set_round_context_overlay("Use a more conversational tone.")
    await agent.perform_action_by_llm()

    first_context = "\n".join(observed_contexts[0])
    assert "Use a more conversational tone." in first_context
    assert "untrusted" in first_context.lower()
    assert agent.system_message.content == original_system_prompt
    persisted_context, _ = agent.memory.get_context()
    assert "Use a more conversational tone." not in "\n".join(
        message["content"] for message in persisted_context
    )

    await agent.perform_action_by_llm()

    second_context = "\n".join(observed_contexts[1])
    assert "Use a more conversational tone." not in second_context
    assert agent.system_message.content == original_system_prompt


@pytest.mark.asyncio
async def test_round_context_overlay_propagates_action_failure_and_clears(
    tmp_path,
) -> None:
    from app.services.decision_lens_oasis_agent import DecisionLensSocialAgent
    from app.services.decision_lens_runtime_adapter import build_runtime_adapters

    artifact, review = approved_pair(tmp_path)
    adapter = build_runtime_adapters(artifact, review)[0]
    agent = DecisionLensSocialAgent(
        adapter=adapter,
        platform="twitter",
        model=_stub_model(),
        available_actions=[ActionType.CREATE_POST],
    )
    agent.env.to_text_prompt = AsyncMock(return_value="Current platform timeline.")
    agent.astep = AsyncMock(side_effect=RuntimeError("model unavailable"))
    agent.set_round_context_overlay("Prefer concise posts.")

    with pytest.raises(RuntimeError, match="model unavailable"):
        await agent.perform_action_by_llm()

    assert agent._round_context_overlay is None


@pytest.mark.asyncio
async def test_each_platform_graph_gets_distinct_exact_prompt_agents(
    tmp_path,
) -> None:
    from app.services.decision_lens_oasis_agent import (
        DecisionLensSocialAgent,
        generate_decision_lens_agent_graph,
    )
    from app.services.decision_lens_runtime_adapter import build_runtime_adapters

    artifact, review = approved_pair(tmp_path)
    adapters = build_runtime_adapters(artifact, review)
    twitter = await generate_decision_lens_agent_graph(
        adapters=adapters,
        platform="twitter",
        model=_stub_model(),
        available_actions=[ActionType.CREATE_POST],
    )
    reddit = await generate_decision_lens_agent_graph(
        adapters=adapters,
        platform="reddit",
        model=_stub_model(),
        available_actions=[ActionType.CREATE_COMMENT],
    )

    assert [agent_id for agent_id, _ in twitter.get_agents()] == list(
        range(len(adapters))
    )
    for adapter in adapters:
        twitter_agent = twitter.get_agent(adapter.agent_id)
        reddit_agent = reddit.get_agent(adapter.agent_id)
        assert isinstance(twitter_agent, DecisionLensSocialAgent)
        assert twitter_agent is not reddit_agent
        assert twitter_agent.system_message.content == adapter.semantic_prompt
        assert reddit_agent.system_message.content == adapter.semantic_prompt
        assert twitter_agent.user_info.recsys_type == "twitter"
        assert reddit_agent.user_info.recsys_type == "reddit"


def test_runtime_loader_requires_reviewed_adapter_artifact(tmp_path) -> None:
    from app.services.decision_lens_oasis_agent import (
        DecisionLensOasisAgentError,
        load_decision_lens_runtime_adapters,
    )
    from app.services.decision_lens_runtime_adapter import build_runtime_adapters

    artifact, review = approved_pair(tmp_path)
    adapters = build_runtime_adapters(artifact, review)
    payload = {
        "schema_version": "decision-lens-runtime/v1",
        "source_artifact_sha256": artifact.artifact_sha256,
        "source_review_sha256": review.review_sha256,
        "adapters": [adapter.model_dump(mode="json") for adapter in adapters],
    }
    (tmp_path / "decision_lens_runtime.v1.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    assert load_decision_lens_runtime_adapters(tmp_path) == adapters

    (tmp_path / "decision_lens_runtime.v1.json").unlink()
    (tmp_path / "twitter_profiles.csv").write_text("legacy", encoding="utf-8")
    with pytest.raises(DecisionLensOasisAgentError) as exc:
        load_decision_lens_runtime_adapters(tmp_path)

    assert exc.value.code == "decision_lens_runtime_required"
