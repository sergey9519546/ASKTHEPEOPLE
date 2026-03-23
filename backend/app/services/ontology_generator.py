"""
Ontology Generation Service
Step 1: Analyze document text and generate entity/relationship type definitions for social simulation.
"""

import json
from typing import Dict, Any, List, Optional
from ..utils.llm_client import LLMClient


# System prompt for ontology generation
ONTOLOGY_SYSTEM_PROMPT = """You are an expert knowledge graph ontology designer. Your task is to analyze the provided text and simulation requirements to design entity types and relationship types suitable for **social media opinion simulation**.

**IMPORTANT: You must output valid JSON only. Do not output anything else.**

## Core Task Context

We are building a **social media opinion simulation system**. In this system:
- Every entity is an "account" or "actor" that can post, interact, and spread information on social media
- Entities influence each other through reposts, comments, and responses
- We need to simulate each party's reaction and the path information spreads during an opinion event

Therefore, **entities must be real-world actors that can speak and interact on social media**:

**Allowed**:
- Specific individuals (public figures, key persons, opinion leaders, experts, ordinary people)
- Companies and enterprises (including their official accounts)
- Organizations (universities, associations, NGOs, unions, etc.)
- Government departments and regulatory agencies
- Media outlets (newspapers, TV stations, online media, websites)
- Social media platforms themselves
- Representative groups (alumni associations, fan groups, advocacy groups, etc.)

**Not allowed**:
- Abstract concepts (e.g., "public opinion", "emotions", "trends")
- Topics / subjects (e.g., "academic integrity", "education reform")
- Stances / attitudes (e.g., "supporters", "opponents")

## Output Format

Output JSON with the following structure:

```json
{
    "entity_types": [
        {
            "name": "EntityTypeName (English, PascalCase)",
            "description": "Short description (English, max 100 chars)",
            "attributes": [
                {
                    "name": "attribute_name (English, snake_case)",
                    "type": "text",
                    "description": "Attribute description"
                }
            ],
            "examples": ["Example entity 1", "Example entity 2"]
        }
    ],
    "edge_types": [
        {
            "name": "RELATIONSHIP_NAME (English, UPPER_SNAKE_CASE)",
            "description": "Short description (English, max 100 chars)",
            "source_targets": [
                {"source": "SourceEntityType", "target": "TargetEntityType"}
            ],
            "attributes": []
        }
    ],
    "analysis_summary": "Brief analysis summary of the document content (English)"
}
```

## Design Guidelines (CRITICAL)

### 1. Entity Type Design — Must Follow Strictly

**Count requirement: Exactly 10 entity types**

**Hierarchy requirement (must include both specific and fallback types)**:

Your 10 entity types must include:

A. **Fallback types (required, place last 2 in the list)**:
   - `Person`: Fallback for any individual person not matching a more specific person type.
   - `Organization`: Fallback for any organization not matching a more specific organization type.

B. **Specific types (8, designed based on document content)**:
   - Design more specific types for the key actors appearing in the document
   - e.g., for an academic event: `Student`, `Professor`, `University`
   - e.g., for a business event: `Company`, `CEO`, `Employee`

**Why fallback types are needed**:
- Documents contain many actors such as "ordinary teachers", "random passerby", "an online user"
- If no specialized type matches, they should fall under `Person`
- Similarly, small organizations and temporary groups should fall under `Organization`

**Specific type design principles**:
- Identify high-frequency or key actor types from the document
- Each specific type should have clear boundaries with minimal overlap
- The description must clearly differentiate it from the fallback type

### 2. Relationship Type Design

- Count: 6–10 types
- Relationships should reflect real connections in social media interactions
- Ensure `source_targets` covers the entity types you defined

### 3. Attribute Design

- 1–3 key attributes per entity type
- **Note**: Do NOT use reserved field names: `name`, `uuid`, `group_id`, `created_at`, `summary`
- Recommended: `full_name`, `title`, `role`, `position`, `location`, `description`, etc.

## Entity Type Reference

**Individuals (specific)**:
- Student, Professor, Journalist, Celebrity, Executive, Official, Lawyer, Doctor

**Individuals (fallback)**:
- Person: Any individual not matching a more specific person type

**Organizations (specific)**:
- University, Company, GovernmentAgency, MediaOutlet, Hospital, School, NGO

**Organizations (fallback)**:
- Organization: Any organization not matching a more specific type

## Relationship Type Reference

- WORKS_FOR, STUDIES_AT, AFFILIATED_WITH, REPRESENTS, REGULATES
- REPORTS_ON, COMMENTS_ON, RESPONDS_TO, SUPPORTS, OPPOSES
- COLLABORATES_WITH, COMPETES_WITH
"""


class OntologyGenerator:
    """
    Ontology Generator.
    Analyzes document text and generates entity and relationship type definitions.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()

    def generate(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate ontology definition.

        Args:
            document_texts: List of document text strings
            simulation_requirement: Description of the simulation goal
            additional_context: Optional extra context

        Returns:
            Ontology definition (entity_types, edge_types, etc.)
        """
        user_message = self._build_user_message(
            document_texts,
            simulation_requirement,
            additional_context
        )

        messages = [
            {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]

        result = self.llm_client.chat_json(
            messages=messages,
            temperature=0.3,
            max_tokens=4096
        )

        result = self._validate_and_process(result)
        return result

    # Maximum text length sent to the LLM (50,000 chars)
    MAX_TEXT_LENGTH_FOR_LLM = 50000

    def _build_user_message(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str]
    ) -> str:
        """Build the user message for the LLM."""

        combined_text = "\n\n---\n\n".join(document_texts)
        original_length = len(combined_text)

        if len(combined_text) > self.MAX_TEXT_LENGTH_FOR_LLM:
            combined_text = combined_text[:self.MAX_TEXT_LENGTH_FOR_LLM]
            combined_text += f"\n\n...(Original document: {original_length} chars. Truncated to first {self.MAX_TEXT_LENGTH_FOR_LLM} chars for ontology analysis)..."

        message = f"""## Simulation Requirement

{simulation_requirement}

## Document Content

{combined_text}
"""

        if additional_context:
            message += f"""
## Additional Notes

{additional_context}
"""

        message += """
Based on the above, design entity types and relationship types suitable for social opinion simulation.

**Rules you must follow**:
1. Output exactly 10 entity types
2. The last 2 must be the fallback types: Person (individual fallback) and Organization (organization fallback)
3. The first 8 are specific types designed based on the document content
4. All entity types must be real-world actors that can speak/post — no abstract concepts
5. Attribute names must NOT use reserved words: name, uuid, group_id — use full_name, org_name, etc.
"""

        return message

    def _validate_and_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and post-process the LLM result."""

        if "entity_types" not in result:
            result["entity_types"] = []
        if "edge_types" not in result:
            result["edge_types"] = []
        if "analysis_summary" not in result:
            result["analysis_summary"] = ""

        for entity in result["entity_types"]:
            if "attributes" not in entity:
                entity["attributes"] = []
            if "examples" not in entity:
                entity["examples"] = []
            if len(entity.get("description", "")) > 100:
                entity["description"] = entity["description"][:97] + "..."

        for edge in result["edge_types"]:
            if "source_targets" not in edge:
                edge["source_targets"] = []
            if "attributes" not in edge:
                edge["attributes"] = []
            if len(edge.get("description", "")) > 100:
                edge["description"] = edge["description"][:97] + "..."

        # Zep API limits: max 10 custom entity types, max 10 custom edge types
        MAX_ENTITY_TYPES = 10
        MAX_EDGE_TYPES = 10

        person_fallback = {
            "name": "Person",
            "description": "Any individual person not fitting other specific person types.",
            "attributes": [
                {"name": "full_name", "type": "text", "description": "Full name of the person"},
                {"name": "role", "type": "text", "description": "Role or occupation"}
            ],
            "examples": ["ordinary citizen", "anonymous netizen"]
        }

        organization_fallback = {
            "name": "Organization",
            "description": "Any organization not fitting other specific organization types.",
            "attributes": [
                {"name": "org_name", "type": "text", "description": "Name of the organization"},
                {"name": "org_type", "type": "text", "description": "Type of organization"}
            ],
            "examples": ["small business", "community group"]
        }

        entity_names = {e["name"] for e in result["entity_types"]}
        has_person = "Person" in entity_names
        has_organization = "Organization" in entity_names

        fallbacks_to_add = []
        if not has_person:
            fallbacks_to_add.append(person_fallback)
        if not has_organization:
            fallbacks_to_add.append(organization_fallback)

        if fallbacks_to_add:
            current_count = len(result["entity_types"])
            needed_slots = len(fallbacks_to_add)
            if current_count + needed_slots > MAX_ENTITY_TYPES:
                to_remove = current_count + needed_slots - MAX_ENTITY_TYPES
                result["entity_types"] = result["entity_types"][:-to_remove]
            result["entity_types"].extend(fallbacks_to_add)

        if len(result["entity_types"]) > MAX_ENTITY_TYPES:
            result["entity_types"] = result["entity_types"][:MAX_ENTITY_TYPES]
        if len(result["edge_types"]) > MAX_EDGE_TYPES:
            result["edge_types"] = result["edge_types"][:MAX_EDGE_TYPES]

        return result

    def generate_python_code(self, ontology: Dict[str, Any]) -> str:
        """
        Convert ontology definition to Python code (similar to ontology.py).

        Args:
            ontology: Ontology definition dict

        Returns:
            Python code string
        """
        code_lines = [
            '"""',
            'Custom entity type definitions.',
            'Auto-generated by ASKTHEPEOPLE for social simulation.',
            '"""',
            '',
            'from pydantic import Field',
            'from zep_cloud.external_clients.ontology import EntityModel, EntityText, EdgeModel',
            '',
            '',
            '# ============== Entity Type Definitions ==============',
            '',
        ]

        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            desc = entity.get("description", f"A {name} entity.")
            code_lines.append(f'class {name}(EntityModel):')
            code_lines.append(f'    """{desc}"""')
            attrs = entity.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: EntityText = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            code_lines.append('')
            code_lines.append('')

        code_lines.append('# ============== Relationship Type Definitions ==============')
        code_lines.append('')

        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            desc = edge.get("description", f"A {name} relationship.")
            code_lines.append(f'class {class_name}(EdgeModel):')
            code_lines.append(f'    """{desc}"""')
            attrs = edge.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: EntityText = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            code_lines.append('')
            code_lines.append('')

        code_lines.append('# ============== Type Configuration ==============')
        code_lines.append('')
        code_lines.append('ENTITY_TYPES = {')
        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            code_lines.append(f'    "{name}": {name},')
        code_lines.append('}')
        code_lines.append('')
        code_lines.append('EDGE_TYPES = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            code_lines.append(f'    "{name}": {class_name},')
        code_lines.append('}')
        code_lines.append('')

        code_lines.append('EDGE_SOURCE_TARGETS = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            source_targets = edge.get("source_targets", [])
            if source_targets:
                st_list = ', '.join([
                    f'{{"source": "{st.get("source", "Entity")}", "target": "{st.get("target", "Entity")}"}}'
                    for st in source_targets
                ])
                code_lines.append(f'    "{name}": [{st_list}],')
        code_lines.append('}')

        return '\n'.join(code_lines)
