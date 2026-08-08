"""Prompt and tool contracts remain immutable for every platform step."""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest


class FakeAgent:
    def __init__(self, agent_id: int, prompt: str, tools: tuple[str, ...]):
        self.social_agent_id = agent_id
        self.system_message = SimpleNamespace(
            role_name="system",
            content=prompt,
        )
        self.tool_dict = {name: object() for name in tools}
        self.user_info = SimpleNamespace(description="transport only")


def test_integrity_guard_detects_prompt_mutation_without_prompt_disclosure() -> None:
    from app.services.instruction_integrity import (
        InstructionIntegrityGuard,
        InstructionIntegrityViolation,
    )

    secret_prompt = "private functional instruction text"
    agent = FakeAgent(0, secret_prompt, ("create_post", "do_nothing"))
    guard = InstructionIntegrityGuard.capture([agent])

    guard.verify([agent])
    agent.user_info.description = "changed transport label"
    guard.verify([agent])
    agent.system_message.content = "mutated prompt"

    with pytest.raises(InstructionIntegrityViolation) as exc:
        guard.verify([agent])

    assert exc.value.code == "instruction_integrity_violation"
    assert secret_prompt not in str(exc.value)
    assert "mutated prompt" not in str(exc.value)


def test_integrity_guard_detects_tool_or_agent_set_mutation() -> None:
    from app.services.instruction_integrity import (
        InstructionIntegrityGuard,
        InstructionIntegrityViolation,
    )

    first = FakeAgent(0, "prompt 0", ("create_post",))
    second = FakeAgent(1, "prompt 1", ("like_post",))
    guard = InstructionIntegrityGuard.capture([first, second])
    first.tool_dict["follow"] = object()

    with pytest.raises(InstructionIntegrityViolation):
        guard.verify([first, second])
    with pytest.raises(InstructionIntegrityViolation):
        guard.verify([second])


def test_integrity_guard_detects_same_name_tool_schema_mutation() -> None:
    from app.services.instruction_integrity import (
        InstructionIntegrityGuard,
        InstructionIntegrityViolation,
    )

    class FakeTool:
        def __init__(self):
            self.schema = {
                "type": "function",
                "function": {
                    "name": "create_post",
                    "description": "Create one synthetic post",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
            self.func = lambda: None

        def get_openai_tool_schema(self):
            return self.schema

    agent = FakeAgent(0, "fixed prompt", ())
    tool = FakeTool()
    agent.tool_dict = {"create_post": tool}
    guard = InstructionIntegrityGuard.capture([agent])
    tool.schema["function"]["description"] = "Mutated tool contract"

    with pytest.raises(InstructionIntegrityViolation):
        guard.verify([agent])


def test_integrity_manifest_contains_hashes_not_prompts() -> None:
    from app.services.instruction_integrity import InstructionIntegrityGuard

    prompt = "instruction content that must not be logged"
    guard = InstructionIntegrityGuard.capture(
        [FakeAgent(0, prompt, ("create_post",))]
    )
    manifest = guard.manifest()

    assert manifest["schema_version"] == "instruction-integrity/v1"
    assert manifest["agents"][0]["agent_id"] == 0
    assert len(manifest["agents"][0]["canonical_sha256"]) == 64
    assert prompt not in str(manifest)


@pytest.mark.asyncio
async def test_checked_step_verifies_before_and_after_even_on_error() -> None:
    from app.services.instruction_integrity import InstructionIntegrityViolation
    from scripts.run_parallel_simulation import integrity_checked_step

    agent = FakeAgent(0, "fixed prompt", ("create_post",))

    class MutatingEnv:
        def __init__(self):
            self.agent_graph = [agent]

        async def step(self, actions):
            agent.system_message.content = "injected replacement"
            raise RuntimeError("platform step failed")

    from app.services.instruction_integrity import InstructionIntegrityGuard

    guard = InstructionIntegrityGuard.capture([agent])
    with pytest.raises(InstructionIntegrityViolation):
        await integrity_checked_step(MutatingEnv(), guard, {agent: object()})


def test_parallel_runner_has_no_legacy_executable_profile_path() -> None:
    from scripts.run_parallel_simulation import (
        run_reddit_simulation,
        run_twitter_simulation,
    )

    twitter_source = inspect.getsource(run_twitter_simulation)
    reddit_source = inspect.getsource(run_reddit_simulation)
    combined = twitter_source + reddit_source

    assert "load_decision_lens_runtime_adapters" in combined
    assert combined.count("generate_decision_lens_agent_graph") == 2
    assert "generate_twitter_agent_graph" not in combined
    assert "generate_reddit_agent_graph" not in combined
    assert "twitter_profiles.csv" not in combined
    assert "reddit_profiles.json" not in combined
    assert "await result.env.step" not in combined
