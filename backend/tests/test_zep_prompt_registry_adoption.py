"""Exec-plan T30: zep_tools adopts the versioned prompt registry.

Four static system prompts were removed from ``app/services/zep_tools.py`` and
now live as YAML definitions under ``app/prompts/definitions/``. Before this
slice ``app/prompts/registry.py`` had five definitions and no production
consumer that reached it from a service module.

Why the wording is duplicated below
-----------------------------------
Each ``EXPECTED_*`` constant is a verbatim copy of the inline literal that was
removed. That duplication *is* the oracle: it is the only thing that can detect
a YAML drift of one character, including the trailing newline that ``|-`` vs
``|`` block-scalar chomping would silently introduce. Do not reword these
constants to match the registry, and do not change the registry to match them:
the wording is the disclosure, and ``AGENTS.md`` section 2 makes these
prohibitions non-dismissible.

What was deliberately NOT adopted
---------------------------------
The four paired ``user_prompt`` f-strings, and the ``combined_prompt`` /
``optimized_prompt`` pair. ``str.format()`` cannot express their interpolations
(conditional expressions, slicing, ``json.dumps``, ``str.join``), so templating
them would have meant rewriting the prompt text. ``user_prompt_template`` is
therefore empty in all four definitions. ``test_user_side_prompts_remain_inline``
pins that.
"""

import ast
import inspect

import pytest

from app.prompts.registry import PromptRegistry
from app.services import zep_tools
from app.services.zep_tools import AgentInterview, ZepToolsService

PROMPT_VERSION = "1.0.0"

# Removed from zep_tools.py at the 1308 system_prompt literal inside _generate_sub_queries().
SUBQUERY_GENERATION = """Decompose a question into conservative retrieval queries over supplied graph material and generated within-run records.

Requirements:
1. Ask about source actors or fictional profile labels without calling them participants.
2. Ask about supplied conditions and generated records without asserting causes or impacts.
3. Ask about the recorded within-run sequence and alternative explanations.
4. Do not frame retrieved material as public opinion, representative behavior, or a forecast.
5. Sub-queries must remain relevant to the supplied scenario context.
6. Return in JSON format: {"sub_queries": ["sub-query 1", "sub-query 2", ...]}"""

# Removed from zep_tools.py at the 1837 system_prompt literal inside _select_agents_for_interview().
PROFILE_SELECTION = """You select fictional generated profiles for a synthetic scenario probe.

These profiles are modelling devices, not human respondents or population
samples. Selection must not imply testimony, public opinion, representative
behavior, probability, or a forecast.

Selection criteria:
1. Cover scenario assumptions relevant to the probe brief.
2. Exercise materially different generated profile states when available.
3. Do not infer real-world views from profession, identity, or demographics.
4. Describe the result as scenario coverage, never sample representativeness.

Return in JSON format:
{
    "selected_indices": [list of selected Agent indices],
    "reasoning": "scenario-coverage assumption for the selection"
}"""

# Removed from zep_tools.py at the 1918 system_prompt literal inside _generate_interview_questions().
PROBE_PROMPT_GENERATION = """Design 3-5 prompts for fictional generated scenario profiles.

The outputs will be synthetic records with zero human respondents. They are not
testimony, public opinion, representative behavior, or forecasts.

Prompt requirements:
1. Ask what the fictional profile might do or surface inside this one scenario.
2. Exercise different stated scenario assumptions without treating roles as real behavior.
3. Do not ask for personal facts, lived experience, feelings, or group representation.
4. Keep each prompt concise (under 50 words).
5. Use conditional language and never request prediction probabilities.

Return in JSON format: {"questions": ["Question 1", "Question 2", ...]}"""

# Removed from zep_tools.py at the 1988 system_prompt literal inside _generate_interview_summary().
PROBE_SUMMARY = """Summarize patterns across fictional generated scenario records.

The records contain zero human respondents. They are not testimony, public
opinion, representative behavior, evidence of consensus, or forecasts.

Summary requirements:
1. Describe only patterns present in the generated records.
2. Call similarities and differences generated-record patterns, never consensus.
3. Do not use direct quotations or attribute lived experience.
4. State material scenario assumptions and limitations.
5. Keep it under 1000 words.

Formatting Constraints (Strictly Follow):
- Use plain text paragraphs, separating different sections with blank lines.
- Do NOT use Markdown headers (e.g., #, ##, ###).
- Do NOT use horizontal rules (e.g., ---, ***).
- You may use **bold** to highlight keywords, but do NOT use other Markdown syntax."""

ADOPTED = {
    "zep_subquery_generation": (PROMPT_VERSION, SUBQUERY_GENERATION),
    "zep_profile_selection": (PROMPT_VERSION, PROFILE_SELECTION),
    "zep_probe_prompt_generation": (PROMPT_VERSION, PROBE_PROMPT_GENERATION),
    "zep_probe_summary": (PROMPT_VERSION, PROBE_SUMMARY),
}

# Pinned by registry.get_sha256, which hashes f"{system_prompt}\n---\n{user_template}".
PINNED_SHA256 = {
    "zep_subquery_generation": "36dd4104db098c17d5e6c83972d3ca9ec0cd8b6ff1f4c74bd05d74edcfd4b7c8",
    "zep_profile_selection": "0d84fc121ce11673f43d2a0a3b876c6349d30ad51972652d28ab5146501ecf2a",
    "zep_probe_prompt_generation": "3fe9ed90d9787783977570230c96444427483c1a92c68543566d7f87523a6b67",
    "zep_probe_summary": "60abab86f4532df5a233bf4128ccc104491ca709dcf5cfb2f1f29e64a16e375d",
}

SOURCE_ONLY_FRAGMENTS = {
    "zep_subquery_generation": "Decompose a question into conservative retrieval queries",
    "zep_profile_selection": (
        "You select fictional generated profiles for a synthetic scenario probe."
    ),
    "zep_probe_prompt_generation": (
        "Design 3-5 prompts for fictional generated scenario profiles."
    ),
    "zep_probe_summary": (
        "Call similarities and differences generated-record patterns, never consensus."
    ),
}

ADOPTED_IDS = sorted(ADOPTED)


class _CapturingLLM:
    """Captures the messages each call site sends, then returns a canned result."""

    def __init__(self, json_result=None, text_result=""):
        self.json_result = json_result or {}
        self.text_result = text_result
        self.calls = []

    def chat_json(self, **kwargs):
        self.calls.append(kwargs)
        return self.json_result

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return self.text_result


def _service(llm):
    service = ZepToolsService.__new__(ZepToolsService)
    service._llm_client = llm
    return service


def _system_message(llm, call_index=0):
    messages = llm.calls[call_index]["messages"]
    assert messages[0]["role"] == "system"
    return messages[0]["content"]


def _registry_text(prompt_id):
    return PromptRegistry().get_prompt(prompt_id, PROMPT_VERSION)["system_prompt"]


# --- the registry serves exactly the text that was removed -------------------


@pytest.mark.parametrize("prompt_id", ADOPTED_IDS)
def test_registry_prompt_text_matches_the_removed_inline_literal(prompt_id):
    """The definition must reproduce the removed literal byte for byte."""
    version, expected = ADOPTED[prompt_id]

    actual = _registry_text(prompt_id)

    assert actual == expected, (
        f"{prompt_id} wording changed: {len(actual)} chars vs {len(expected)}"
    )


@pytest.mark.parametrize("prompt_id", ADOPTED_IDS)
def test_registry_prompt_keeps_the_exact_trailing_whitespace_shape(prompt_id):
    """`|-` chomping is load-bearing; `|` would append one newline.

    None of the removed literals ended in a newline, so a definition written
    with default `|` chomping would still compare equal under a naive
    ``in``/``strip`` assertion and only fail here.
    """
    _, expected = ADOPTED[prompt_id]

    actual = _registry_text(prompt_id)

    assert not actual.endswith("\n")
    assert actual == actual.rstrip("\n")
    assert expected == expected.rstrip("\n")


@pytest.mark.parametrize("prompt_id", ADOPTED_IDS)
def test_registry_sha256_is_pinned(prompt_id):
    """The audit fingerprint is pinned, so any content edit fails loudly."""
    registry = PromptRegistry()

    assert registry.get_sha256(prompt_id, PROMPT_VERSION) == PINNED_SHA256[prompt_id]


@pytest.mark.parametrize("prompt_id", ADOPTED_IDS)
def test_definition_file_declares_the_registry_shape(prompt_id):
    """The new files carry the same top-level keys as the pre-existing ones."""
    reference = PromptRegistry().get_prompt("ontology_generation", "1.0.0")

    definition = PromptRegistry().get_prompt(prompt_id, PROMPT_VERSION)

    assert set(definition) == set(reference)
    assert definition["id"] == prompt_id
    assert definition["version"] == PROMPT_VERSION
    assert definition["tools"] == []
    assert definition["validators"], "a prompt with no validators is unrecorded"


@pytest.mark.parametrize("prompt_id", ADOPTED_IDS)
def test_zep_tools_module_no_longer_carries_the_prompt_wording(prompt_id):
    """The wording must be gone from the module, not copied next to the registry.

    Without this, an implementation that kept the inline literal and merely
    *also* registered it would satisfy every equality test above.
    """
    source = inspect.getsource(zep_tools)

    assert SOURCE_ONLY_FRAGMENTS[prompt_id] not in source


def test_zep_tools_declares_no_inline_system_prompt_literals():
    """No bare triple-quoted `system_prompt` literal remains in the module."""
    tree = ast.parse(inspect.getsource(zep_tools))
    constants = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(t, ast.Name) and t.id == "system_prompt"
            for t in node.targets
        )
        and isinstance(node.value, ast.Constant)
    ]

    assert constants == [], (
        "an inline static system_prompt literal is back in zep_tools.py; "
        "the registry is the single source for this wording"
    )


# --- the call sites actually read the registry -------------------------------


def test_generate_sub_queries_sends_the_registry_system_prompt():
    llm = _CapturingLLM(json_result={"sub_queries": ["a", "b"]})
    service = _service(llm)

    queries = service._generate_sub_queries(
        "weekend transit change",
        "fictional transit scenario",
        max_queries=4,
    )

    assert queries == ["a", "b"]
    assert _system_message(llm) == _registry_text("zep_subquery_generation")


def test_select_agents_for_interview_sends_the_registry_system_prompt():
    llm = _CapturingLLM(
        json_result={"selected_indices": [0], "reasoning": "Scenario coverage only."}
    )
    service = _service(llm)
    profiles = [{"realname": "Profile A", "profession": "Student", "bio": "seed"}]

    selected, indices, reasoning = service._select_agents_for_interview(
        profiles,
        "Explore a supplied assumption",
        "Fictional transit scenario",
        1,
    )

    assert (selected, indices, reasoning) == (profiles, [0], "Scenario coverage only.")
    assert _system_message(llm) == _registry_text("zep_profile_selection")


def test_generate_interview_questions_sends_the_registry_system_prompt():
    llm = _CapturingLLM(json_result={"questions": ["What path appears?"]})
    service = _service(llm)

    questions = service._generate_interview_questions(
        "Explore a supplied assumption",
        "Fictional transit scenario",
        [{"realname": "Profile A", "profession": "Student"}],
    )

    assert questions == ["What path appears?"]
    assert _system_message(llm) == _registry_text("zep_probe_prompt_generation")


def test_generate_interview_summary_sends_the_registry_system_prompt():
    llm = _CapturingLLM(text_result="Generated-record pattern summary.")
    service = _service(llm)

    summary = service._generate_interview_summary(
        [
            AgentInterview(
                agent_name="Profile A",
                agent_role="Student",
                agent_bio="seed",
                question="What path appears?",
                response="A generated response.",
            )
        ],
        "weekend transit",
    )

    assert summary == "Generated-record pattern summary."
    assert _system_message(llm) == _registry_text("zep_probe_summary")


# --- the registry is loaded lazily ------------------------------------------


def test_prompt_registry_is_not_constructed_at_import_time():
    """Importing zep_tools must not read the definitions directory.

    A module-level `PromptRegistry()` call would run during app import, so a
    malformed definition file would raise before any try/except existed to
    absorb it -- the failure `llm_client.py` goes out of its way to avoid.
    """
    tree = ast.parse(inspect.getsource(zep_tools))
    module_level_bindings = [
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "_prompt_registry"
    ]

    assert len(module_level_bindings) == 1, (
        "expected exactly one module-level _prompt_registry binding; a second "
        "one would be a construction at import time"
    )
    assert isinstance(module_level_bindings[0].value, ast.Constant)
    assert module_level_bindings[0].value.value is None


def test_registry_singleton_is_reused_across_calls(monkeypatch):
    """After the first successful load the registry is cached, not rebuilt."""
    monkeypatch.setattr(zep_tools, "_prompt_registry", None)
    service = _service(_CapturingLLM(json_result={"sub_queries": []}))

    service._generate_sub_queries("q", "fictional scenario")

    first = zep_tools._prompt_registry
    assert isinstance(first, PromptRegistry)

    service._generate_sub_queries("q", "fictional scenario")

    assert zep_tools._prompt_registry is first


# --- a registry failure must never reach a caller ----------------------------


class _BrokenRegistry:
    def __init__(self, *_args, **_kwargs):
        raise RuntimeError("definitions directory unavailable")


@pytest.fixture
def broken_registry(monkeypatch):
    monkeypatch.setattr(zep_tools, "PromptRegistry", _BrokenRegistry)
    monkeypatch.setattr(zep_tools, "_prompt_registry", None)


def test_broken_registry_does_not_escape_sub_query_generation(broken_registry):
    """A prompt-registry problem must not 500 a simulation."""
    service = _service(_CapturingLLM(json_result={"sub_queries": ["never sent"]}))

    queries = service._generate_sub_queries(
        "weekend transit change",
        "fictional transit scenario",
        max_queries=4,
    )

    assert queries == [
        "weekend transit change",
        "Source actors or fictional profile labels associated with weekend transit change",
        "Supplied conditions and generated records associated with weekend transit change",
        "Recorded within-run sequence and alternative explanations for weekend transit change",
    ]
    assert service._llm_client.calls == [], "the LLM must not be called without a prompt"


def test_broken_registry_does_not_escape_profile_selection(broken_registry):
    service = _service(_CapturingLLM(json_result={"selected_indices": [1]}))
    profiles = [
        {"realname": "Profile A"},
        {"realname": "Profile B"},
    ]

    selected, indices, reasoning = service._select_agents_for_interview(
        profiles,
        "Explore a supplied assumption",
        "Fictional transit scenario",
        1,
    )

    assert selected == profiles[:1]
    assert indices == [0]
    assert reasoning == (
        "Automatic fictional profile selection; not a representative sample."
    )


def test_broken_registry_does_not_escape_probe_generation(broken_registry):
    service = _service(_CapturingLLM(json_result={"questions": ["never sent"]}))

    questions = service._generate_interview_questions(
        "Explore a supplied assumption",
        "Fictional transit scenario",
        [{"realname": "Profile A", "profession": "Student"}],
    )

    assert len(questions) == 3
    assert "Within this fictional scenario" in questions[0]


def test_broken_registry_does_not_escape_probe_summary(broken_registry):
    service = _service(_CapturingLLM(text_result="never sent"))
    interviews = [
        AgentInterview(
            agent_name="Profile A",
            agent_role="Student",
            agent_bio="seed",
            question="What path appears?",
            response="A generated response.",
        )
    ]

    summary = service._generate_interview_summary(interviews, "weekend transit")

    assert summary.startswith(
        "Fictional generated scenario records; 0 human respondents; "
        "not public opinion or a forecast."
    )


def test_broken_registry_logs_a_privacy_safe_warning(broken_registry, monkeypatch):
    """The failure is logged, and the log carries no prompt or scenario text."""
    warnings = []
    monkeypatch.setattr(
        zep_tools.logger,
        "warning",
        lambda message, *args, **kwargs: warnings.append(
            message % args if args else str(message)
        ),
    )
    service = _service(_CapturingLLM(json_result={"sub_queries": []}))

    service._generate_sub_queries(
        "private-simulation-requirement-814f",
        "private-scenario-text",
    )

    assert warnings
    rendered = "\n".join(warnings)
    assert "code=prompt_registry_unavailable" in rendered
    assert "private-simulation-requirement-814f" not in rendered
    assert "private-scenario-text" not in rendered


def test_unknown_prompt_id_degrades_instead_of_raising(tmp_path, monkeypatch):
    """A registry that loads but is missing the definition is the same failure.

    `PromptRegistry._load_prompts` raises on a malformed file, and `get_prompt`
    raises on an unknown id; both must be absorbed the same way as an
    unreadable definitions directory.
    """
    monkeypatch.setattr(
        zep_tools, "_prompt_registry", PromptRegistry(definitions_path=tmp_path)
    )
    service = _service(_CapturingLLM(json_result={"sub_queries": ["never sent"]}))

    queries = service._generate_sub_queries("q", "fictional scenario")

    assert queries[0] == "q"
    assert service._llm_client.calls == []


def test_a_malformed_definition_file_degrades_instead_of_raising(tmp_path, monkeypatch):
    """A definition missing `id`/`version` raises at load, and must not escape.

    The construction has to happen inside the call site for this to test
    anything: `PromptRegistry.__init__` raises, so the module has to build it
    lazily for `_get_prompt_registry` to be the thing that absorbs the error.
    """
    (tmp_path / "broken.yaml").write_text("description: no id or version\n", "utf-8")
    monkeypatch.setattr(
        zep_tools,
        "PromptRegistry",
        lambda *args, **kwargs: PromptRegistry(definitions_path=tmp_path),
    )
    monkeypatch.setattr(zep_tools, "_prompt_registry", None)
    service = _service(_CapturingLLM(json_result={"sub_queries": ["never sent"]}))

    queries = service._generate_sub_queries("q", "fictional scenario")

    assert queries[0] == "q"
    assert service._llm_client.calls == []
    assert zep_tools._prompt_registry is None


# --- the user-side prompts were deliberately left alone ----------------------


@pytest.mark.parametrize("prompt_id", ADOPTED_IDS)
def test_user_side_prompts_remain_inline(prompt_id):
    """`user_prompt_template` is empty by design; the f-strings stay in the module.

    Templating them would require rewriting them, so this test records the
    decision rather than leaving it to a reader's guesswork.
    """
    definition = PromptRegistry().get_prompt(prompt_id, PROMPT_VERSION)

    assert definition["user_prompt_template"] == ""


def test_user_prompt_wording_is_still_built_in_the_module():
    source = inspect.getsource(zep_tools)
    user_fragments = [
        "Please decompose the following query into",
        "Select up to {max_agents} generated profiles for scenario coverage",
        "Generate 3-5 conditional scenario-probe prompts.",
        "Summarize only generated-record patterns and begin with this exact disclosure",
    ]

    for fragment in user_fragments:
        assert fragment in source, f"user-side prompt fragment moved: {fragment!r}"
