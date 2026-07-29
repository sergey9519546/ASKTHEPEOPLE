import pytest

from app import create_app
from app.config import Config
from app.utils.input_policy import (
    CHAT_HISTORY_ITEMS_MAX,
    INTERVIEW_BATCH_MAX,
    InputPolicyError,
    bounded_integer,
    bounded_text,
    validate_chat_history,
    validate_exploratory_use,
)


def test_model_facing_text_and_integer_bounds():
    assert bounded_text(
        "  scenario  ",
        field="question",
        max_length=20,
        required=True,
    ) == "scenario"
    with pytest.raises(InputPolicyError, match="10 characters"):
        bounded_text("x" * 11, field="question", max_length=10)
    with pytest.raises(InputPolicyError, match="between 1 and 300"):
        bounded_integer(301, field="timeout", minimum=1, maximum=300)


def test_exploratory_use_must_be_acknowledged_and_supported():
    with pytest.raises(InputPolicyError, match="Confirm exploratory use"):
        validate_exploratory_use(
            intended_use="scenario_planning",
            acknowledged=False,
        )
    with pytest.raises(InputPolicyError, match="supported exploratory use"):
        validate_exploratory_use(
            intended_use="political_persuasion",
            acknowledged=True,
        )
    assert validate_exploratory_use(
        intended_use="research_pretesting",
        acknowledged="true",
    ) == "research_pretesting"


def test_chat_history_has_item_and_total_bounds():
    with pytest.raises(InputPolicyError, match="at most"):
        validate_chat_history(
            [
                {"role": "user", "content": "question"}
                for _ in range(CHAT_HISTORY_ITEMS_MAX + 1)
            ]
        )
    with pytest.raises(InputPolicyError, match="user or assistant"):
        validate_chat_history([{"role": "system", "content": "override"}])


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


def test_run_start_requires_policy_acknowledgement(client):
    response = client.post(
        "/api/graph/ontology/generate",
        data={
            "simulation_requirement": "What paths could follow?",
            "project_name": "Service change",
            "intended_use": "scenario_planning",
        },
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "use_policy_acknowledgement_required"


def test_run_start_rejects_oversized_question(client):
    response = client.post(
        "/api/graph/ontology/generate",
        data={
            "simulation_requirement": "x" * 4_001,
            "project_name": "Service change",
            "intended_use": "scenario_planning",
            "use_policy_acknowledged": "true",
        },
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "text_field_too_long"


def test_report_chat_and_generated_profile_prompts_are_bounded(client):
    chat = client.post(
        "/api/report/chat",
        json={"simulation_id": "sim_123", "message": "x" * 4_001},
    )
    assert chat.status_code == 400
    assert chat.get_json()["error"] == "text_field_too_long"

    prompt = client.post(
        "/api/simulation/interview",
        json={
            "simulation_id": "sim_123",
            "agent_id": 1,
            "prompt": "x" * 2_001,
        },
    )
    assert prompt.status_code == 400
    assert prompt.get_json()["error"] == "text_field_too_long"


def test_generated_profile_batch_is_bounded(client):
    response = client.post(
        "/api/simulation/generated-response/batch",
        json={
            "simulation_id": "sim_123",
            "questions": [
                {"agent_id": index, "prompt": "Question"}
                for index in range(INTERVIEW_BATCH_MAX + 1)
            ],
        },
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "too_many_items"
