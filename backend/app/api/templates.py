from flask import jsonify
from . import graph_bp

# Predefined question frames for ordinary, reversible decision pretesting.
# High-risk political persuasion, financial-market, regulatory-compliance, and
# crisis-manipulation starters are deliberately excluded.
TEMPLATES = [
    {
        "id": "service_change",
        "name": "Public service change",
        "description": "Explore how different groups could experience a proposed change to schedules, access, or delivery.",
        "prompt_base": "What plausible paths could follow if this public service change is introduced? Treat every path as a synthetic possibility to test, not a prediction.",
        "suggested_ontology_goal": "Map affected groups, access constraints, operational dependencies, and the assumptions that most need real-world validation.",
        "human_validation_required": True,
    },
    {
        "id": "product_decision",
        "name": "Product decision",
        "description": "Surface adoption barriers, misunderstandings, and second-order effects before a product change ships.",
        "prompt_base": "What different paths could follow if this product decision is made? Explore plausible reactions without claiming to measure customers or forecast adoption.",
        "suggested_ontology_goal": "Map user contexts, jobs to be done, switching costs, support needs, and assumptions to validate with customers.",
        "human_validation_required": True,
    },
    {
        "id": "operations_rollout",
        "name": "Operations rollout",
        "description": "Stress-test a process, staffing, or logistics change against several plausible operating conditions.",
        "prompt_base": "What could happen under different operating conditions if this process change is introduced? Explore failure paths and recovery options.",
        "suggested_ontology_goal": "Map roles, handoffs, resource constraints, dependencies, and observable signals for a limited pilot.",
        "human_validation_required": True,
    },
    {
        "id": "community_program",
        "name": "Community program",
        "description": "Explore participation barriers and unintended effects before piloting a voluntary local program.",
        "prompt_base": "What plausible participation and access paths could follow from this community program? Do not infer public opinion from the generated scenarios.",
        "suggested_ontology_goal": "Map participant contexts, trusted intermediaries, accessibility constraints, opt-out needs, and questions for community interviews.",
        "human_validation_required": True,
    },
    {
        "id": "message_clarity",
        "name": "Message clarity",
        "description": "Find ways an informational message could be misread before testing it with its intended audience.",
        "prompt_base": "How could different contexts change the way this informational message is interpreted? Generate ambiguity paths, not persuasion targets.",
        "suggested_ontology_goal": "Map prerequisite knowledge, ambiguous terms, accessibility needs, information channels, and comprehension questions for real participants.",
        "human_validation_required": True,
    },
    {
        "id": "fictional_world",
        "name": "Fictional world",
        "description": "Explore faction dynamics and consequences inside an explicitly fictional narrative.",
        "prompt_base": "Within this fictional setting, what different paths could follow from the inciting event?",
        "suggested_ontology_goal": "Map fictional factions, relationships, resources, tensions, and the narrative assumptions that drive each branch.",
        "human_validation_required": False,
    },
]

@graph_bp.route('/templates', methods=['GET'])
def list_templates():
    """
    Get all pre-defined simulation templates
    """
    return jsonify({
        "success": True,
        "data": TEMPLATES,
        "human_respondents": 0,
        "calibration": "not_calibrated",
        "disclosure": "Question frames generate synthetic scenarios, not forecasts or public opinion.",
    })
