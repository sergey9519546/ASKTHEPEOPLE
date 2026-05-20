from flask import jsonify
from . import graph_bp

# Predefined templates for social simulation domains
TEMPLATES = [
    {
        "id": "political",
        "name": "Political Discourse",
        "description": "Simulate how policy proposals or political events spread through different social strata and interest groups.",
        "icon": "⚖️",
        "prompt_base": "Analyze the following documents to identify key political actors, interest groups, and media influencers. The goal is to simulate the shift in public opinion regarding a specific political event or policy.",
        "suggested_ontology_goal": "Identify government officials, opposition leaders, grassroots activists, and media outlets. Focus on mapping ideological stances and influence paths."
    },
    {
        "id": "brand",
        "name": "Brand Crisis Management",
        "description": "Predict consumer sentiment shifts and test the effectiveness of PR responses during a brand scandal or product failure.",
        "icon": "🛡️",
        "prompt_base": "Identify brand representatives, consumer advocates, legal experts, and viral influencers involved in a brand event. Simulate the spread of sentiment and the impact of corporate communications.",
        "suggested_ontology_goal": "Identify key consumer segments, corporate spokespeople, industry analysts, and regulatory bodies. Focus on trust metrics and sentiment propagation."
    },
    {
        "id": "creative",
        "name": "Narrative Worldbuilding",
        "description": "Explore power dynamics, faction conflicts, and social structures within a fictional world or complex narrative scenario.",
        "icon": "✍️",
        "prompt_base": "Extract the social hierarchy, faction leaders, and historical tensions from the narrative documents. Simulate how a disruptive event affects the existing social order.",
        "suggested_ontology_goal": "Map factions, their leaders, and the conflicting ideologies. Focus on social hierarchy and faction loyalty/rivalry."
    }
]

@graph_bp.route('/templates', methods=['GET'])
def list_templates():
    """
    Get all pre-defined simulation templates
    """
    return jsonify({
        "success": True,
        "data": TEMPLATES
    })
