"""
Tests for the LLMClient role contract (P0 prompt-prefixing fix).

Per the audit (ASKTHEPEOPLE_GODMODE_BUILDPLAN.md §5 P0 "Prompt
prefixing is not a security boundary"), the role contract:

- Uses separate system + user roles. The fixed prefix lives in
  the system role; the user-controlled content lives in the
  user role.
- Binds zero tools. The OpenAI `tools` parameter is NEVER passed
  to the chat.completions.create call.
- Requests structured output (JSON mode). A JSON decode failure
  raises and is never silently coerced to a valid-looking empty
  object.
- Runs deterministic truth + terminology validators on the
  response and attaches the audit to the result.
- Records the prompt template ID, the model release alias, the
  system and user prompt hashes, the output hash, and the
  per-call configuration to the result.
"""

import json
import hashlib
import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from app.utils.llm_client import LLMClient


def _make_fake_response(content: str):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason="stop",
            )
        ]
    )


def test_role_contract_returns_data_and_record():
    """Happy path: the contract returns the parsed data and the
    per-call record. The record carries the model alias, the
    system + user prompt hashes, the output hash, the
    structured_output flag, the tools_bound flag, and the
    truth audit.
    """
    fake = MagicMock()
    fake.chat.completions.create.return_value = _make_fake_response(
        json.dumps({"bio": "x", "persona": "y"})
    )
    with patch("app.utils.llm_client.OpenAI", return_value=fake):
        client = LLMClient(api_key="x", base_url="https://x", model="m1")
        result = client.chat_with_role_contract(
            system_prompt="sys",
            user_prompt="usr",
        )

    assert result["data"] == {"bio": "x", "persona": "y"}
    assert result["model"] == "m1"
    assert result["tools_bound"] is False
    assert result["structured_output"] is True
    assert result["system_prompt_sha256"] == hashlib.sha256(b"sys").hexdigest()
    assert result["user_prompt_sha256"] == hashlib.sha256(b"usr").hexdigest()
    assert result["output_sha256"] == hashlib.sha256(
        json.dumps({"bio": "x", "persona": "y"}).encode("utf-8")
    ).hexdigest()
    assert "truth_audit" in result
    assert result["truth_audit"]["prohibited_term_hits"] == []


def test_role_contract_binds_zero_tools():
    """The OpenAI call MUST NOT pass a `tools` parameter. This
    test asserts the call kwargs do not contain `tools` and that
    the returned `tools_bound` flag is False. The audit P0 finding
    names "Bind zero tools" as a required correction.
    """
    fake = MagicMock()
    fake.chat.completions.create.return_value = _make_fake_response(
        json.dumps({"bio": "x", "persona": "y"})
    )
    with patch("app.utils.llm_client.OpenAI", return_value=fake):
        client = LLMClient(api_key="x", base_url="https://x", model="m1")
        client.chat_with_role_contract(system_prompt="sys", user_prompt="usr")

    kwargs = fake.chat.completions.create.call_args.kwargs
    assert "tools" not in kwargs
    assert "functions" not in kwargs
    assert "tool_choice" not in kwargs
    # And the call requests JSON mode (structured output).
    assert kwargs.get("response_format") == {"type": "json_object"}


def test_role_contract_separates_system_and_user():
    """The call MUST have exactly one system message and one user
    message (when no context prompts are provided). The fixed
    prefix lives in the system role; the user content lives in
    the user role. The audit calls out "concatenates a fixed
    prefix with user input" as the failure mode.
    """
    fake = MagicMock()
    fake.chat.completions.create.return_value = _make_fake_response(
        json.dumps({"bio": "x", "persona": "y"})
    )
    with patch("app.utils.llm_client.OpenAI", return_value=fake):
        client = LLMClient(api_key="x", base_url="https://x", model="m1")
        client.chat_with_role_contract(
            system_prompt="<SYS>do not invent</SYS>",
            user_prompt="<USR>name: Alice</USR>",
        )

    messages = fake.chat.completions.create.call_args.kwargs["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "<SYS>do not invent</SYS>"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "<USR>name: Alice</USR>"


def test_role_contract_context_comes_before_user():
    """Context prompts (e.g. extracted source text) come BEFORE the
    user content. The user content remains the last role seen by
    the model so the context cannot displace it.
    """
    fake = MagicMock()
    fake.chat.completions.create.return_value = _make_fake_response(
        json.dumps({"bio": "x", "persona": "y"})
    )
    with patch("app.utils.llm_client.OpenAI", return_value=fake):
        client = LLMClient(api_key="x", base_url="https://x", model="m1")
        client.chat_with_role_contract(
            system_prompt="sys",
            user_prompt="USR",
            context_prompts=["CTX1", "CTX2"],
        )

    messages = fake.chat.completions.create.call_args.kwargs["messages"]
    assert [m["role"] for m in messages] == ["system", "user", "user", "user"]
    assert [m["content"] for m in messages] == ["sys", "CTX1", "CTX2", "USR"]


def test_role_contract_raises_on_invalid_json():
    """JSON decode failure raises and is never silently coerced to
    a valid-looking empty object. The audit requires distinguishing
    schema-decode failures from real responses.
    """
    fake = MagicMock()
    fake.chat.completions.create.return_value = _make_fake_response("not json")
    with patch("app.utils.llm_client.OpenAI", return_value=fake):
        client = LLMClient(api_key="x", base_url="https://x", model="m1")
        with pytest.raises(ValueError, match="invalid JSON"):
            client.chat_with_role_contract(
                system_prompt="sys",
                user_prompt="usr",
            )


def test_role_contract_raises_on_empty_inputs():
    """Empty system or user prompts are rejected. The contract
    refuses to make an LLM call with no system role (which would
    silently degrade the role split) or no user role.
    """
    fake = MagicMock()
    with patch("app.utils.llm_client.OpenAI", return_value=fake):
        client = LLMClient(api_key="x", base_url="https://x", model="m1")
        with pytest.raises(ValueError, match="system_prompt is required"):
            client.chat_with_role_contract(system_prompt="", user_prompt="u")
        with pytest.raises(ValueError, match="user_prompt is required"):
            client.chat_with_role_contract(system_prompt="s", user_prompt="")


def test_role_contract_audits_prohibited_terms():
    """The deterministic truth + terminology validator records
    prohibited terms in the audit. The audit does not block; it
    records. Gate 5 lands the block-on-violation behavior.
    """
    fake = MagicMock()
    # Output that includes several prohibited terms. The audit does
    # not block; it records hits in the truth_audit field.
    fake.chat.completions.create.return_value = _make_fake_response(
        json.dumps({
            "bio": "x",
            "persona": "y",
            "note": "this respondent represents a public opinion poll result",
        })
    )
    with patch("app.utils.llm_client.OpenAI", return_value=fake):
        client = LLMClient(api_key="x", base_url="https://x", model="m1")
        result = client.chat_with_role_contract(
            system_prompt="sys",
            user_prompt="usr",
        )
    hits = result["truth_audit"]["prohibited_term_hits"]
    assert "respondent" in hits
    assert "public opinion" in hits
    assert "poll result" in hits


def test_role_contract_handles_markdown_fences():
    """The contract strips markdown ```json ... ``` fences before
    parsing, matching the existing LLMClient.chat_json() behavior.
    """
    fake = MagicMock()
    fake.chat.completions.create.return_value = _make_fake_response(
        "```json\n{\"bio\": \"x\", \"persona\": \"y\"}\n```"
    )
    with patch("app.utils.llm_client.OpenAI", return_value=fake):
        client = LLMClient(api_key="x", base_url="https://x", model="m1")
        result = client.chat_with_role_contract(
            system_prompt="sys",
            user_prompt="usr",
        )
    assert result["data"] == {"bio": "x", "persona": "y"}
