"""Chain-of-thought must not reach report text (ADRs 0004 / 0007 / 0010).

Section text is normally taken from after the "Final Answer:" marker, which
leaves the ReACT preamble behind. Two paths in _generate_section_react adopt the
model's response whole when that marker is absent — the "sufficient tool calls
but no prefix" path and the forced-closure path — and the section prompt asks
the model for "Thought (Thought)" and "Action" steps. So on those paths the
reasoning preamble became the published section, reaching full_report.md,
GET /api/report/<id>, the agent log, and every export bundle.
"""

import pytest

from app.services.report_agent import strip_reasoning_scaffold

# --------------------------------------------------------------------------- #
# Tagged reasoning is removed wherever it appears
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("tag", ["thinking", "think", "reasoning", "scratchpad", "reflection"])
def test_tagged_reasoning_blocks_are_removed(tag):
    text = f"<{tag}>the model deliberating</{tag}>\nThe synthetic runs diverged."
    result = strip_reasoning_scaffold(text)
    assert "deliberating" not in result
    assert "The synthetic runs diverged." in result


def test_tagged_reasoning_is_removed_mid_text_not_only_at_the_start():
    text = "Opening prose.\n<thinking>hidden</thinking>\nClosing prose."
    result = strip_reasoning_scaffold(text)
    assert "hidden" not in result
    assert "Opening prose." in result
    assert "Closing prose." in result


def test_tag_matching_is_case_insensitive_and_tolerates_attributes():
    text = '<Thinking depth="high">hidden</Thinking>\nBody.'
    assert "hidden" not in strip_reasoning_scaffold(text)


def test_tool_call_blocks_are_removed():
    text = "<tool_call>{\"name\": \"search\"}</tool_call>\nBody text."
    result = strip_reasoning_scaffold(text)
    assert "tool_call" not in result
    assert "Body text." in result


# --------------------------------------------------------------------------- #
# ReACT scaffold: leading run only
# --------------------------------------------------------------------------- #

def test_leading_react_preamble_is_removed():
    text = (
        "Thought: I should look at the diffusion output first.\n"
        "Action: query_simulation_data\n"
        "Observation: 40 synthetic profiles responded.\n"
        "\n"
        "Across the synthetic runs, responses clustered into two groups."
    )
    result = strip_reasoning_scaffold(text)
    assert result == "Across the synthetic runs, responses clustered into two groups."


def test_action_input_step_is_recognised():
    text = "Action Input: {\"query\": \"x\"}\nReal body."
    assert strip_reasoning_scaffold(text) == "Real body."


def test_scaffold_words_inside_report_prose_are_kept():
    """"Action:" further down is plausible report copy, not scaffolding.

    Over-deleting a recommendations section is worse than leaving a stray
    preamble line, so the scaffold strip is a leading run only.
    """
    text = (
        "The synthetic exploration surfaced two tensions.\n"
        "Action: broaden outreach to the under-represented segment.\n"
        "Observation decks should be reviewed quarterly."
    )
    result = strip_reasoning_scaffold(text)
    assert "broaden outreach" in result
    assert "Observation decks" in result


def test_bold_wrapped_labels_are_kept():
    """The prompt tells the model to use **bold** instead of sub-headers."""
    text = "**Action:** broaden outreach.\n**Observation:** uptake was uneven."
    result = strip_reasoning_scaffold(text)
    assert "broaden outreach" in result
    assert "uptake was uneven" in result


def test_body_without_any_scaffold_is_returned_unchanged():
    text = "A clean section body with no scaffolding at all."
    assert strip_reasoning_scaffold(text) == text


# --------------------------------------------------------------------------- #
# Degenerate inputs
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("value", ["", None])
def test_empty_input_yields_empty_string(value):
    assert strip_reasoning_scaffold(value) == ""


def test_all_scaffold_yields_empty_rather_than_leaking():
    text = "Thought: only thinking here.\nAction: nothing else."
    assert strip_reasoning_scaffold(text) == ""


def test_result_is_stripped_of_surrounding_whitespace():
    assert strip_reasoning_scaffold("\n\n  Body.  \n\n") == "Body."


# --------------------------------------------------------------------------- #
# The finalisation paths call it
# --------------------------------------------------------------------------- #

def test_every_section_finalisation_path_scrubs():
    """Pins the call sites, so a new path cannot quietly skip the scrub."""
    import inspect

    from app.services.report_agent import ReportAgent

    source = inspect.getsource(ReportAgent._generate_section_react)
    # Three finalisation points: normal marker split, no-marker adoption,
    # forced-closure. Each must route through the scrubber.
    assert source.count("strip_reasoning_scaffold") >= 3
    # And none of them may adopt the raw response directly any more.
    assert "final_answer = response\n" not in source
    assert "final_answer = response.strip()" not in source
