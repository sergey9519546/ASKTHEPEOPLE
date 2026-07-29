from app.services.simulation_config_generator import SimulationConfigGenerator
from app.services.role_normalizer import normalize_entity_type
from app.services.simulation_artifacts import (
    _build_activity_seed,
    _build_platform_overrides,
)
from app.services.zep_entity_reader import EntityNode
from app.services.zep_tools import (
    AgentInterview,
    InterviewResult,
    PanoramaResult,
    SYNTHETIC_PROBE_PROMPT_PREFIX,
)


class _CapturingConfigCall:
    def __init__(self, result):
        self.result = result
        self.prompt = ""
        self.system_prompt = ""

    def __call__(self, prompt, system_prompt):
        self.prompt = prompt
        self.system_prompt = system_prompt
        return self.result


class _CapturingLLM:
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


class _FailingLLM:
    def chat_json(self, **kwargs):
        raise RuntimeError("offline")


def _entity(name, label):
    return EntityNode(
        uuid=f"uuid-{name}",
        name=name,
        labels=["Entity", label],
        summary="Source-derived graph summary.",
        attributes={},
    )


def test_panorama_and_probe_render_as_unverified_synthetic_records():
    panorama = PanoramaResult(
        query="What paths are present?",
        active_facts=["Generated relation"],
        total_nodes=2,
        total_edges=1,
        active_count=1,
    ).to_text()

    assert "wide graph record search" in panorama.lower()
    assert "origin is unverified" in panorama.lower()
    assert "no future claim is implied" in panorama.lower()
    assert "future panorama" not in panorama.lower()

    generated_record = AgentInterview(
        agent_name="Profile A",
        agent_role="Student",
        agent_bio="Synthetic seed",
        question="What path appears?",
        response="A generated path appears under the supplied assumption.",
        key_quotes=["A generated excerpt with enough material to retain."],
    )
    result = InterviewResult(
        interview_topic="Weekend transit",
        interview_questions=["What path appears?"],
        interviews=[generated_record],
        selection_reasoning="Fictional scenario coverage.",
        summary="A pattern across generated records.",
        total_agents=3,
        interviewed_count=1,
    )

    rendered = result.to_text().lower()
    assert "synthetic perspective probe" in rendered
    assert "0 human respondents" in rendered
    assert "not testimony" in rendered
    assert "public opinion" in rendered
    assert "not a forecast" in rendered
    assert "generated scenario records" in rendered
    assert "selected generated excerpts (not quotations)" in rendered
    for legacy_label in (
        "deep interview report",
        "number of interviewees",
        "interview transcripts",
        "key quotes",
        "interview summary",
    ):
        assert legacy_label not in rendered

    payload = result.to_dict()
    assert payload["fictional"] is True
    assert payload["human_respondents"] == 0
    assert payload["is_testimony"] is False
    assert payload["is_public_opinion"] is False
    assert payload["is_representative"] is False
    assert payload["is_forecast"] is False
    assert payload["generated_record_count"] == 1
    assert payload["interviews"][0]["human_respondents"] == 0
    assert payload["interview_topic"] == "Weekend transit"


def test_synthetic_probe_engine_prompt_rejects_respondent_claims():
    prompt = SYNTHETIC_PROBE_PROMPT_PREFIX.lower()

    assert "fictional generated scenario record" in prompt
    assert "not claim to be a real person or respondent" in prompt
    assert "testimony" in prompt
    assert "public opinion" in prompt
    assert "representative behavior" in prompt
    assert "forecast" in prompt
    assert "participating in an interview" not in prompt


def test_probe_planning_prompts_select_scenario_coverage_not_a_sample():
    from app.services.zep_tools import ZepToolsService

    service = ZepToolsService.__new__(ZepToolsService)
    service._llm_client = _CapturingLLM(
        {"selected_indices": [0], "reasoning": "Scenario coverage only."}
    )
    profiles = [
        {
            "realname": "Profile A",
            "profession": "Student",
            "bio": "Synthetic seed",
        }
    ]

    selected, indices, reasoning = service._select_agents_for_interview(
        profiles,
        "Explore a supplied assumption",
        "Fictional transit scenario",
        1,
    )

    assert selected == profiles
    assert indices == [0]
    assert reasoning == "Scenario coverage only."
    planning_prompt = " ".join(
        "\n".join(
            message["content"]
            for message in service._llm_client.calls[0]["messages"]
        )
        .lower()
        .split()
    )
    assert "fictional generated profiles" in planning_prompt
    assert "not human respondents or population samples" in planning_prompt
    assert "do not infer real-world views from profession" in planning_prompt
    assert "never sample representativeness" in planning_prompt

    service._llm_client = _CapturingLLM({"questions": ["What path appears?"]})
    questions = service._generate_interview_questions(
        "Explore a supplied assumption",
        "Fictional transit scenario",
        profiles,
    )
    question_prompt = "\n".join(
        message["content"]
        for message in service._llm_client.calls[0]["messages"]
    ).lower()
    assert questions == ["What path appears?"]
    assert "zero human respondents" in question_prompt
    assert "do not ask for personal facts" in question_prompt
    assert "group representation" in question_prompt
    assert "as in a real interview" not in question_prompt


def test_query_decomposition_fallback_avoids_causal_and_participant_claims():
    from app.services.zep_tools import ZepToolsService

    service = ZepToolsService.__new__(ZepToolsService)
    service._llm_client = _FailingLLM()

    queries = service._generate_sub_queries(
        "weekend transit change",
        "fictional transit scenario",
        max_queries=4,
    )
    combined = "\n".join(queries).lower()

    assert "source actors or fictional profile labels" in combined
    assert "supplied conditions and generated records" in combined
    assert "recorded within-run sequence and alternative explanations" in combined
    assert "main participants" not in combined
    assert "causes and impacts" not in combined
    assert "development process" not in combined


def test_context_language_does_not_default_to_china_or_beijing():
    generator = SimulationConfigGenerator.__new__(SimulationConfigGenerator)

    cjk_only = generator._infer_context_profile(
        simulation_requirement="周末公交服务场景",
        document_text="探索若干假设路径。",
        entities=[],
    )
    assert cjk_only["language"] == "zh"
    assert cjk_only["country"] == "Unknown"
    assert cjk_only["timezone"] == "UTC"
    assert cjk_only["activity_norm"] == "fictional_cadence_default"
    assert cjk_only["human_respondents"] == 0
    assert "not participant behavior" in cjk_only["methodology"]

    explicit_place = generator._infer_context_profile(
        simulation_requirement="A scenario explicitly set in Beijing",
        document_text="",
        entities=[],
    )
    assert explicit_place["country"] == "China"
    assert explicit_place["timezone"] == "Asia/Shanghai"
    assert "no population behavior was inferred" in explicit_place["reasoning"]


def test_time_prompt_uses_neutral_fictional_clock_not_locale_habits():
    generator = SimulationConfigGenerator.__new__(SimulationConfigGenerator)
    capture = _CapturingConfigCall(
        {
            "total_simulation_hours": 72,
            "minutes_per_round": 60,
            "agents_per_hour_min": 1,
            "agents_per_hour_max": 2,
            "reasoning": "Fictional cadence.",
        }
    )
    generator._call_llm_with_retry = capture

    generator._generate_time_config("Synthetic context", 10)
    combined = f"{capture.system_prompt}\n{capture.prompt}".lower()

    assert "fictional run-clock" in combined
    assert "timezone in the context is only the clock" in combined
    assert "do not infer schedules or activity from nationality" in combined
    assert "not observed behavior" in combined
    assert "people from china" not in combined
    assert "beijing time" not in combined
    assert "typical activity habits" not in combined
    assert "student group peak" not in combined


def test_agent_controls_are_neutral_without_explicit_source_constraints():
    generator = SimulationConfigGenerator.__new__(SimulationConfigGenerator)
    capture = _CapturingConfigCall({"agent_configs": []})
    generator._call_llm_with_retry = capture
    entities = [
        _entity("Profile A", "Student"),
        _entity("Profile B", "GovernmentAgency"),
    ]

    configs = generator._generate_agent_configs_batch(
        context="Synthetic context",
        entities=entities,
        start_idx=0,
        simulation_requirement="Explore paths",
    )
    combined = f"{capture.system_prompt}\n{capture.prompt}".lower()

    assert "fictional run assumptions" in combined
    assert "do not infer activity" in combined
    assert "profession, nationality, demographics, or role labels" in combined
    assert "use neutral values" in combined
    assert "fictional active-hour buckets" in combined
    assert "explicit supplied scheduling constraints" in combined
    assert "otherwise 9-22" in combined
    assert "for the inferred locale" not in combined
    assert "realistic local active hours" not in combined
    assert "official agencies" not in combined
    assert "individuals" not in combined

    left = configs[0]
    right = configs[1]
    behavioral_fields = (
        "activity_level",
        "posts_per_hour",
        "comments_per_hour",
        "active_hours",
        "response_delay_min",
        "response_delay_max",
        "sentiment_bias",
        "stance",
        "influence_weight",
        "reaction_style",
        "conflict_tolerance",
        "authority_sensitivity",
        "novelty_seeking",
        "platform_preference",
    )
    assert all(
        getattr(left, field_name) == getattr(right, field_name)
        for field_name in behavioral_fields
    )
    assert left.normalized_role != right.normalized_role

    bootstrap = generator._build_network_bootstrap(configs, True, True)
    assert bootstrap["enable_follow_bootstrap"] is False
    assert bootstrap["graph_relationship_behavior_opt_in"] is False
    assert bootstrap["role_bias_rules"] == {}
    assert bootstrap["relationship_affinity_rules"] == {}
    assert bootstrap["relationship_behavior_inferred"] is False
    assert bootstrap["assumption_basis"] == "neutral_fictional_default"
    assert bootstrap["record_origin"] == "graph_record_origin_unverified"
    assert bootstrap["external_validation"] is False
    assert bootstrap["causal_evidence"] is False
    assert "no role-based human behavior" in bootstrap["assumption_disclosure"]


def test_unverified_llm_behavioral_overrides_are_machine_neutralized():
    generator = SimulationConfigGenerator.__new__(SimulationConfigGenerator)
    generator._call_llm_with_retry = _CapturingConfigCall(
        {
            "agent_configs": [
                {
                    "agent_id": 0,
                    "activity_level": 0.99,
                    "posts_per_hour": 9.0,
                    "comments_per_hour": 12.0,
                    "active_hours": [0, 1, 2],
                    "response_delay_min": 0,
                    "response_delay_max": 1,
                    "sentiment_bias": 0.9,
                    "stance": "supportive",
                    "influence_weight": 8.0,
                    "reaction_style": "amplifying",
                    "conflict_tolerance": 0.95,
                    "authority_sensitivity": 0.95,
                    "novelty_seeking": 0.95,
                    "platform_preference": "twitter",
                }
            ]
        }
    )
    entity = _entity("Profile A", "GovernmentAgency")

    config = generator._generate_agent_configs_batch(
        context="Synthetic context",
        entities=[entity],
        start_idx=0,
        simulation_requirement="Explore paths",
    )[0]

    assert config.activity_level == 0.5
    assert config.posts_per_hour == 0.5
    assert config.comments_per_hour == 1.0
    assert config.active_hours == list(range(9, 23))
    assert config.response_delay_min == 5
    assert config.response_delay_max == 60
    assert config.sentiment_bias == 0.0
    assert config.stance == "neutral"
    assert config.influence_weight == 1.0
    assert config.reaction_style == "measured"
    assert config.conflict_tolerance == 0.45
    assert config.authority_sensitivity == 0.4
    assert config.novelty_seeking == 0.45
    assert config.platform_preference == "both"
    assert config.control_assumption_basis == "neutral_fictional_default"
    assert config.behavioral_override_applied is False
    assert config.measured_human_behavior is False
    assert config.human_respondents == 0
    assert config.causal_evidence is False


def test_role_normalization_is_structural_and_platform_defaults_are_neutral():
    raw_roles = (
        "Student",
        "MediaOutlet",
        "GovernmentAgency",
        "PublicFigure",
        "UnknownCustomLabel",
    )
    roles = [normalize_entity_type(raw_role) for raw_role in raw_roles]

    assert len({role["normalized_role"] for role in roles}) > 1
    assert all(
        role["default_platform_presence"] == {"twitter": 0.7, "reddit": 0.7}
        for role in roles
    )
    assert all(
        role["platform_presence_basis"] == "neutral_fictional_default"
        for role in roles
    )
    assert all(role["human_respondents"] == 0 for role in roles)
    assert all(
        "structural source-label normalization only" in role["reasoning"].lower()
        for role in roles
    )
    assert all(
        "does not infer behavior, platform preference" in role["reasoning"].lower()
        for role in roles
    )


def test_artifact_activity_and_platform_defaults_do_not_change_by_role():
    role_infos = [
        normalize_entity_type("Student"),
        normalize_entity_type("MediaOutlet"),
        normalize_entity_type("GovernmentAgency"),
    ]

    activity_seeds = [_build_activity_seed(role) for role in role_infos]
    platform_overrides = [_build_platform_overrides(role) for role in role_infos]

    assert activity_seeds[1:] == activity_seeds[:-1]
    assert platform_overrides[1:] == platform_overrides[:-1]

    seed = activity_seeds[0]
    assert seed["platform_preference"] == "both"
    assert seed["assumption_basis"] == "neutral_fictional_default"
    assert seed["human_respondents"] == 0
    assert seed["role_behavior_inferred"] is False
    assert "role labels do not supply behavioral evidence" in seed["disclosure"]

    overrides = platform_overrides[0]
    assert (
        overrides["twitter"]["assumption_basis"]
        == "neutral_fictional_default"
    )
    assert (
        overrides["reddit"]["assumption_basis"]
        == "neutral_fictional_default"
    )
    assert overrides["methodology"]["human_respondents"] == 0
    assert overrides["methodology"]["role_behavior_inferred"] is False
    assert "no role-based behavior" in overrides["methodology"]["disclosure"]
