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
    },
    {
        "id": "crisis_pr",
        "name": "Crisis PR & Counter-Narrative",
        "description": "Test real-time counter-narratives, press releases, and executive statements against viral public backlash.",
        "icon": "🚨",
        "prompt_base": "Identify corporate executives, investigative journalists, vocal critics, and industry observers. Simulate how live statement injections alter public perception and hashtag virality.",
        "suggested_ontology_goal": "Map corporate spokespeople, media outlets, boycotters, and industry regulators. Focus on trust degradation and recovery vectors."
    },
    {
        "id": "market_panic",
        "name": "Financial Market & Rumor Panic",
        "description": "Simulate bank runs, speculative asset dumps, or liquidity panics triggered by social media rumor cascades.",
        "icon": "📉",
        "prompt_base": "Identify institutional investors, retail day traders, short sellers, and financial news outlets. Model how unverified rumors propagate across trader communities.",
        "suggested_ontology_goal": "Map market whales, retail trader hubs, financial analysts, and regulatory agencies. Focus on panic contagion and liquidity sentiment."
    },
    {
        "id": "product_launch",
        "name": "Product Launch & Viral Adoption",
        "description": "Simulate consumer tech launches, early adopter reviews, feature feedback loops, and word-of-mouth growth.",
        "icon": "🚀",
        "prompt_base": "Identify tech reviewers, early adopters, skeptical power users, and competitor advocates. Model post-launch feature reaction and organic community referral networks.",
        "suggested_ontology_goal": "Map tech influencers, power users, casual consumers, and rival brand loyalists. Focus on feature sentiment and viral reach."
    },
    {
        "id": "policy_shift",
        "name": "Regulatory & Policy Shift",
        "description": "Evaluate stakeholder compliance, lobbying resistance, and public adoption of new regulatory frameworks.",
        "icon": "🏛️",
        "prompt_base": "Identify regulatory bodies, corporate compliance officers, consumer advocacy groups, and trade unions. Model public adaptation to new legislation.",
        "suggested_ontology_goal": "Map government agencies, industry lobbies, consumer groups, and legal experts. Focus on compliance likelihood and institutional friction."
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
