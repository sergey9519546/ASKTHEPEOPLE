from app.api.templates import TEMPLATES


def test_question_starters_exclude_prohibited_high_risk_frames():
    rendered = " ".join(
        str(value)
        for template in TEMPLATES
        for value in template.values()
    ).lower()

    for prohibited in (
        "political persuasion",
        "election",
        "market panic",
        "bank run",
        "asset dump",
        "counter-narrative",
        "lobbying resistance",
    ):
        assert prohibited not in rendered


def test_question_starters_disclose_human_validation_requirement():
    assert TEMPLATES
    assert all(
        isinstance(template.get("human_validation_required"), bool)
        for template in TEMPLATES
    )
    assert any(template["human_validation_required"] for template in TEMPLATES)
