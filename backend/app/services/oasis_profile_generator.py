"""
OASIS Agent Profile Generator.
Converts entities from the Zep knowledge graph into Agent Profile format required by the OASIS simulation platform.

Key improvements:
1. Uses Zep retrieval to enrich node information with additional context
2. Optimised prompts for generating highly detailed personas
3. Distinguishes individual entities from abstract group/institutional entities
"""

import json
import random
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from openai import OpenAI
from zep_cloud.client import Zep

from ..config import Config
from ..utils.logger import get_logger
from .zep_entity_reader import EntityNode, ZepEntityReader

logger = get_logger('askthepeople.oasis_profile')


@dataclass
class OasisAgentProfile:
    """Data structure for an OASIS Agent Profile."""
    # Common fields
    user_id: int
    user_name: str
    name: str
    bio: str
    persona: str
    
    # Reddit-style optional fields
    karma: int = 1000
    
    # Twitter-style optional fields
    friend_count: int = 100
    follower_count: int = 150
    statuses_count: int = 500
    
    # Extra persona info
    age: Optional[int] = None
    gender: Optional[str] = None
    mbti: Optional[str] = None
    country: Optional[str] = None
    profession: Optional[str] = None
    interested_topics: List[str] = field(default_factory=list)
    
    # Source entity info
    source_entity_uuid: Optional[str] = None
    source_entity_type: Optional[str] = None
    
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    
    def to_reddit_format(self) -> Dict[str, Any]:
        """Convert to Reddit platform format."""
        profile = {
            "realname": self.name,
            "username": self.user_name,
            "bio": (self.bio or self.name).replace("\n", " ").replace("\r", " "),
            "persona": (self.persona or self.bio or self.name).replace("\n", " ").replace("\r", " "),
            "age": self.age if self.age else 30,
            "gender": self.gender if self.gender else "other",
            "mbti": self.mbti if self.mbti else "ISTJ",
            "country": self.country if self.country else "Unknown",
        }

        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics

        return profile
    
    def to_twitter_format(self) -> Dict[str, Any]:
        """Convert to Twitter platform format."""
        user_char = (self.persona or self.bio or self.name).replace("\n", " ").replace("\r", " ")
        description = (self.bio or self.name).replace("\n", " ").replace("\r", " ")
        return {
            "user_id": self.user_id,
            "name": self.name,
            "username": self.user_name,
            "user_char": user_char,
            "description": description,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to full dictionary format."""
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "age": self.age,
            "gender": self.gender,
            "mbti": self.mbti,
            "country": self.country,
            "profession": self.profession,
            "interested_topics": self.interested_topics,
            "source_entity_uuid": self.source_entity_uuid,
            "source_entity_type": self.source_entity_type,
            "created_at": self.created_at,
        }


class OasisProfileGenerator:
    """
    OASIS Profile Generator.
    
    Converts Zep graph entities into Agent Profiles required for OASIS simulation.
    
    Key features:
    1. Uses Zep graph retrieval for richer context per entity
    2. Generates highly detailed personas (background, career, personality, social media behaviour, etc.)
    3. Distinguishes individual entities from group/institutional entities
    """
    
    # MBTI type list
    MBTI_TYPES = [
        "INTJ", "INTP", "ENTJ", "ENTP",
        "INFJ", "INFP", "ENFJ", "ENFP",
        "ISTJ", "ISFJ", "ESTJ", "ESFJ",
        "ISTP", "ISFP", "ESTP", "ESFP"
    ]
    
    # Common countries
    COUNTRIES = [
        "China", "US", "UK", "Japan", "Germany", "France", 
        "Canada", "Australia", "Brazil", "India", "South Korea"
    ]
    
    # Individual entity types (generate specific personal personas)
    INDIVIDUAL_ENTITY_TYPES = [
        "student", "alumni", "professor", "person", "publicfigure", 
        "expert", "faculty", "official", "journalist", "activist"
    ]
    
    # Group / institutional entity types (generate representative account personas)
    GROUP_ENTITY_TYPES = [
        "university", "governmentagency", "organization", "ngo", 
        "mediaoutlet", "company", "institution", "group", "community"
    ]
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        zep_api_key: Optional[str] = None,
        graph_id: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model_name = model_name or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY is not configured")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # Zep client for enriching context via retrieval
        self.zep_api_key = zep_api_key or Config.ZEP_API_KEY
        self.zep_client = None
        self.graph_id = graph_id
        
        if self.zep_api_key:
            try:
                self.zep_client = Zep(api_key=self.zep_api_key)
            except Exception as e:
                logger.warning(f"Zep client initialisation failed: {e}")
    
    def generate_profile_from_entity(
        self, 
        entity: EntityNode, 
        user_id: int,
        use_llm: bool = True
    ) -> OasisAgentProfile:
        """
        Generate an OASIS Agent Profile from a Zep entity.
        
        Args:
            entity: Zep entity node
            user_id: User ID for OASIS
            use_llm: Whether to use LLM to generate a detailed persona
            
        Returns:
            OasisAgentProfile
        """
        entity_type = entity.get_entity_type() or "Entity"
        
        # Basic info
        name = entity.name
        user_name = self._generate_username(name)
        
        # Build context
        context = self._build_entity_context(entity)
        
        if use_llm:
            # Use LLM to generate a detailed persona
            profile_data = self._generate_profile_with_llm(
                entity_name=name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes,
                context=context
            )
        else:
            # Use rule-based fallback for basic persona
            profile_data = self._generate_profile_rule_based(
                entity_name=name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes
            )
        
        return OasisAgentProfile(
            user_id=user_id,
            user_name=user_name,
            name=name,
            bio=profile_data.get("bio", f"{entity_type}: {name}"),
            persona=profile_data.get("persona", entity.summary or f"A {entity_type} named {name}."),
            karma=profile_data.get("karma", random.randint(500, 5000)),
            friend_count=profile_data.get("friend_count", random.randint(50, 500)),
            follower_count=profile_data.get("follower_count", random.randint(100, 1000)),
            statuses_count=profile_data.get("statuses_count", random.randint(100, 2000)),
            age=profile_data.get("age"),
            gender=profile_data.get("gender"),
            mbti=profile_data.get("mbti"),
            country=profile_data.get("country"),
            profession=profile_data.get("profession"),
            interested_topics=profile_data.get("interested_topics", []),
            source_entity_uuid=entity.uuid,
            source_entity_type=entity_type,
        )
    
    def _generate_username(self, name: str) -> str:
        """Generate a username from entity name."""
        # Remove special characters and convert to lowercase
        username = name.lower().replace(" ", "_")
        username = ''.join(c for c in username if c.isalnum() or c == '_')
        
        # Add random suffix to avoid collisions
        suffix = random.randint(100, 999)
        return f"{username}_{suffix}"
    
    def _search_zep_for_entity(self, entity: EntityNode) -> Dict[str, Any]:
        """
        Use Zep graph hybrid search to retrieve rich information related to the entity
        
        Zep has no built-in hybrid search interface; edges and nodes must be searched separately and results merged.
        Use parallel requests to search simultaneously and improve efficiency.
        
        Args:
            entity: Entity node object
            
        Returns:
            Dictionary containing facts, node_summaries, and context
        """
        import concurrent.futures
        
        if not self.zep_client:
            return {"facts": [], "node_summaries": [], "context": ""}
        
        entity_name = entity.name
        
        results = {
            "facts": [],
            "node_summaries": [],
            "context": ""
        }
        
        # graph_id is required for search
        if not self.graph_id:
            logger.debug(f"Skipping Zep retrieval: graph_id not set")
            return results
        
        comprehensive_query = f"All information, activities, events, relationships and background for {entity_name}"
        
        def search_edges():
            """Search edges (facts/relationships) with retry logic."""
            max_retries = 3
            last_exception = None
            delay = 2.0
            
            for attempt in range(max_retries):
                try:
                    return self.zep_client.graph.search(
                        query=comprehensive_query,
                        graph_id=self.graph_id,
                        limit=30,
                        scope="edges",
                        reranker="rrf"
                    )
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.debug(f"Zep edge search attempt {attempt + 1} failed: {str(e)[:80]}, retrying...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.debug(f"Zep edge search failed after {max_retries} attempts: {e}")
            return None
        
        def search_nodes():
            """Search nodes (entity summaries) with retry logic."""
            max_retries = 3
            last_exception = None
            delay = 2.0
            
            for attempt in range(max_retries):
                try:
                    return self.zep_client.graph.search(
                        query=comprehensive_query,
                        graph_id=self.graph_id,
                        limit=20,
                        scope="nodes",
                        reranker="rrf"
                    )
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.debug(f"Zep node search attempt {attempt + 1} failed: {str(e)[:80]}, retrying...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.debug(f"Zep node search failed after {max_retries} attempts: {e}")
            return None
        
        try:
            # Execute searches for edges and nodes in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                edge_future = executor.submit(search_edges)
                node_future = executor.submit(search_nodes)
                
                # Get results
                edge_result = edge_future.result(timeout=30)
                node_result = node_future.result(timeout=30)
            
            # Process edge search results
            all_facts = set()
            if edge_result and hasattr(edge_result, 'edges') and edge_result.edges:
                for edge in edge_result.edges:
                    if hasattr(edge, 'fact') and edge.fact:
                        all_facts.add(edge.fact)
            results["facts"] = list(all_facts)
            
            # Process node search results
            all_summaries = set()
            if node_result and hasattr(node_result, 'nodes') and node_result.nodes:
                for node in node_result.nodes:
                    if hasattr(node, 'summary') and node.summary:
                        all_summaries.add(node.summary)
                    if hasattr(node, 'name') and node.name and node.name != entity_name:
                        all_summaries.add(f"Related entity: {node.name}")
            results["node_summaries"] = list(all_summaries)
            
            # Build combined context
            context_parts = []
            if results["facts"]:
                context_parts.append("Facts:\n" + "\n".join(f"- {f}" for f in results["facts"][:20]))
            if results["node_summaries"]:
                context_parts.append("Related entities:\n" + "\n".join(f"- {s}" for s in results["node_summaries"][:10]))
            results["context"] = "\n\n".join(context_parts)
            
            logger.info(f"Zep hybrid retrieval complete: {entity_name}, {len(results['facts'])} facts, {len(results['node_summaries'])} related nodes")
            
        except concurrent.futures.TimeoutError:
            logger.warning(f"Zep retrieval timed out ({entity_name})")
        except Exception as e:
            logger.warning(f"Zep retrieval failed ({entity_name}): {e}")
        
        return results
    
    def _build_entity_context(self, entity: EntityNode) -> str:
        """
        Build the complete context for an entity, including:
        1. Entity attribute information
        2. Related edge information (facts)
        3. Additional information retrieved via Zep hybrid search
        """
        context_parts = []
        
        # 1. Entity attributes
        if entity.attributes:
            attrs = []
            for key, value in entity.attributes.items():
                if value and str(value).strip():
                    attrs.append(f"- {key}: {value}")
            if attrs:
                context_parts.append("### Entity Attributes\n" + "\n".join(attrs))
        
        # 2. Related edge info (facts / relationships)
        existing_facts = set()
        if entity.related_edges:
            relationships = []
            for edge in entity.related_edges:
                fact = edge.get("fact", "")
                edge_name = edge.get("edge_name", "")
                direction = edge.get("direction", "")
                
                if fact:
                    relationships.append(f"- {fact}")
                    existing_facts.add(fact)
                elif edge_name:
                    if direction == "outgoing":
                        relationships.append(f"- {entity.name} --[{edge_name}]--> (related entity)")
                    else:
                        relationships.append(f"- (related entity) --[{edge_name}]--> {entity.name}")
            
            if relationships:
                context_parts.append("### Related Facts and Relationships\n" + "\n".join(relationships))
        
        # 3. Related node details
        if entity.related_nodes:
            related_info = []
            for node in entity.related_nodes:
                node_name = node.get("name", "")
                node_labels = node.get("labels", [])
                node_summary = node.get("summary", "")
                
                # Filter out default labels
                custom_labels = [l for l in node_labels if l not in ["Entity", "Node"]]
                label_str = f" ({', '.join(custom_labels)})" if custom_labels else ""
                
                if node_summary:
                    related_info.append(f"- **{node_name}**{label_str}: {node_summary}")
                else:
                    related_info.append(f"- **{node_name}**{label_str}")
            
            if related_info:
                context_parts.append("### Related Entity Details\n" + "\n".join(related_info))
        
        # 4. Enrich with Zep hybrid retrieval
        zep_results = self._search_zep_for_entity(entity)
        
        if zep_results.get("facts"):
            # De-duplicate: exclude facts already captured above
            new_facts = [f for f in zep_results["facts"] if f not in existing_facts]
            if new_facts:
                context_parts.append("### Additional Facts from Zep\n" + "\n".join(f"- {f}" for f in new_facts[:15]))
        
        if zep_results.get("node_summaries"):
            context_parts.append("### Related Nodes from Zep\n" + "\n".join(f"- {s}" for s in zep_results["node_summaries"][:10]))
        
        return "\n\n".join(context_parts)
    
    def _is_individual_entity(self, entity_type: str) -> bool:
        """Return True if the entity type represents an individual person."""
        return entity_type.lower() in self.INDIVIDUAL_ENTITY_TYPES
    
    def _is_group_entity(self, entity_type: str) -> bool:
        """Return True if the entity type represents a group or institution."""
        return entity_type.lower() in self.GROUP_ENTITY_TYPES
    
    def _generate_profile_with_llm(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> Dict[str, Any]:
        """
        Use the LLM to generate a highly detailed persona.
        
        Dispatches by entity type:
        - Individual entity: generates a specific personal persona
        - Group / institutional entity: generates a representative account persona
        """
        
        is_individual = self._is_individual_entity(entity_type)
        
        if is_individual:
            prompt = self._build_individual_persona_prompt(
                entity_name, entity_type, entity_summary, entity_attributes, context
            )
        else:
            prompt = self._build_group_persona_prompt(
                entity_name, entity_type, entity_summary, entity_attributes, context
            )

        # Retry up to max_attempts times
        max_attempts = 3
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self._get_system_prompt(is_individual)},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1)  # Lower temperature on each retry
                )
                
                content = response.choices[0].message.content
                
                # Check if output was truncated
                finish_reason = response.choices[0].finish_reason
                if finish_reason == 'length':
                    logger.warning(f"LLM output truncated (attempt {attempt+1}), attempting fix...")
                    content = self._fix_truncated_json(content)
                
                # Attempt JSON parse
                try:
                    result = json.loads(content)
                    
                    # Validate required fields
                    if "bio" not in result or not result["bio"]:
                        result["bio"] = entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}"
                    if "persona" not in result or not result["persona"]:
                        result["persona"] = entity_summary or f"{entity_name} is a {entity_type}."
                    
                    return result
                    
                except json.JSONDecodeError as je:
                    logger.warning(f"JSON parse failed (attempt {attempt+1}): {str(je)[:80]}")
                    
                    # Attempt JSON repair
                    result = self._try_fix_json(content, entity_name, entity_type, entity_summary)
                    if result.get("_fixed"):
                        del result["_fixed"]
                        return result
                    
                    last_error = je
                    
            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt+1}): {str(e)[:80]}")
                last_error = e
                import time
                time.sleep(1 * (attempt + 1))  # Exponential backoff
        
        logger.warning(f"LLM persona generation failed after {max_attempts} attempts: {last_error}, falling back to rule-based")
        return self._generate_profile_rule_based(
            entity_name, entity_type, entity_summary, entity_attributes
        )
    
    def _fix_truncated_json(self, content: str) -> str:
        """Attempt to repair JSON truncated by token limits."""
        import re
        
        content = content.strip()
        
        # Count unclosed brackets
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')
        
        # Close any open string
        if content and content[-1] not in '",}]':
            content += '"'
        
        # Close brackets
        content += ']' * open_brackets
        content += '}' * open_braces
        
        return content
    
    def _try_fix_json(self, content: str, entity_name: str, entity_type: str, entity_summary: str = "") -> Dict[str, Any]:
        """Attempt to repair corrupted JSON"""
        import re
        
        # 1. First attempt to repair truncation
        content = self._fix_truncated_json(content)
        
        # 2. Attempt to extract the JSON part
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()
            
            # 3. Handle newline characters within strings
            # Find all string values and replace newlines within them
            def fix_string_newlines(match):
                s = match.group(0)
                # Replace actual newlines within strings with spaces
                s = s.replace('\n', ' ').replace('\r', ' ')
                # Replace redundant spaces
                s = re.sub(r'\s+', ' ', s)
                return s
            
            # Match JSON string values
            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string_newlines, json_str)
            
            # 4. Attempt to parse
            try:
                result = json.loads(json_str)
                result["_fixed"] = True
                return result
            except json.JSONDecodeError as e:
                # 5. If still failed, attempt more aggressive repair
                try:
                    # Remove all control characters
                    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                    # Replace all consecutive whitespaces
                    json_str = re.sub(r'\s+', ' ', json_str)
                    result = json.loads(json_str)
                    result["_fixed"] = True
                    return result
                except:
                    pass
        
        # 6. Try to extract partial info from the content
        bio_match = re.search(r'"bio"\s*:\s*"([^"]*)"', content)
        persona_match = re.search(r'"persona"\s*:\s*"([^"]*)', content)  # may be truncated
        
        bio = bio_match.group(1) if bio_match else (entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}")
        persona = persona_match.group(1) if persona_match else (entity_summary or f"{entity_name} is a {entity_type}.")
        
        # If we extracted something meaningful, mark as fixed
        if bio_match or persona_match:
            logger.info(f"Extracted partial info from malformed JSON")
            return {
                "bio": bio,
                "persona": persona,
                "_fixed": True
            }
        
        # 7. Complete failure - return minimal structure
        logger.warning(f"JSON repair failed, returning minimal structure")
        return {
            "bio": entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}",
            "persona": entity_summary or f"{entity_name} is a {entity_type}."
        }
    
    def _get_system_prompt(self, is_individual: bool) -> str:
        """Return the system prompt for persona generation."""
        base_prompt = "You are an expert social media user persona designer. Generate detailed, realistic personas for opinion simulation that closely reflect known real-world facts. You MUST return valid JSON. All string values must not contain unescaped newline characters. Write all text in English."
        return base_prompt
    
    def _build_individual_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> str:
        """Build the persona prompt for an individual entity."""
        
        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "None"
        context_str = context[:3000] if context else "No additional context"
        
        return f"""Generate a detailed social media user persona for the following entity, staying as close as possible to known real-world facts.

Entity name: {entity_name}
Entity type: {entity_type}
Entity summary: {entity_summary}
Entity attributes: {attrs_str}

Context:
{context_str}

Return a JSON object with these fields:

1. bio: Social media bio (~200 words)
2. persona: Detailed persona description (~2000 words, plain text), covering:
   - Background (age, occupation, education, location)
   - Personal history (key experiences, connection to the event, social relationships)
   - Personality (MBTI type, core traits, emotional expression)
   - Social media behaviour (posting frequency, content preferences, interaction style, language)
   - Stance and opinions (attitude toward the topic, what provokes or moves them)
   - Unique traits (catchphrases, special experiences, hobbies)
   - Personal memory (individual's known actions and reactions regarding this event)
3. age: Integer
4. gender: English string, exactly "male" or "female"
5. mbti: MBTI type (e.g. INTJ, ENFP)
6. country: Country name in English
7. profession: Occupation
8. interested_topics: Array of topic strings

IMPORTANT:
- All field values must be strings or numbers - no newline characters in values
- persona must be a single block of coherent text
- Write everything in English (gender must be "male" or "female")
- Content must be consistent with the entity information provided
- age must be a valid integer
"""

    def _build_group_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> str:
        """Build the persona prompt for a group or institutional entity."""
        
        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "None"
        context_str = context[:3000] if context else "No additional context"
        
        return f"""Generate a detailed social media account profile for the following institutional or group entity, staying as close as possible to known real-world facts.

Entity name: {entity_name}
Entity type: {entity_type}
Entity summary: {entity_summary}
Entity attributes: {attrs_str}

Context:
{context_str}

Return a JSON object with these fields:

1. bio: Official account bio (~200 words, professional tone)
2. persona: Detailed account profile (~2000 words, plain text), covering:
   - Institutional background (official name, nature, founding context, key functions)
   - Account positioning (account type, target audience, core purpose)
   - Communication style (language features, common expressions, sensitive topics to avoid)
   - Content characteristics (content types, posting frequency, active time slots)
   - Official stance (position on key topics, how controversies are handled)
   - Special notes (the community this account represents, operational habits)
   - Institutional memory (known actions and reactions of this institution regarding this event)
3. age: Always 30 (virtual age for institutional accounts)
4. gender: Always "other" (institutional accounts use "other")
5. mbti: MBTI type describing account style (e.g. ISTJ = formal and conservative)
6. country: Country name in English
7. profession: Institutional function description
8. interested_topics: Array of topic strings

IMPORTANT:
- All field values must be strings or numbers - no null values, no newlines in values
- persona must be a single block of coherent text
- Write everything in English (gender must be the string "other")
- age must be the integer 30, gender must be the string "other"
- Communications must match the institution's identity and positioning"""
    
    def _generate_profile_rule_based(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a basic persona using rule-based fallback logic."""
        
        entity_type_lower = entity_type.lower()
        
        if entity_type_lower in ["student", "alumni"]:
            return {
                "bio": f"{entity_type} with interests in academics and social issues.",
                "persona": f"{entity_name} is a {entity_type.lower()} who is actively engaged in academic and social discussions. They enjoy sharing perspectives and connecting with peers.",
                "age": random.randint(18, 30),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(self.MBTI_TYPES),
                "country": random.choice(self.COUNTRIES),
                "profession": "Student",
                "interested_topics": ["Education", "Social Issues", "Technology"],
            }
        
        elif entity_type_lower in ["publicfigure", "expert", "faculty"]:
            return {
                "bio": f"Expert and thought leader in their field.",
                "persona": f"{entity_name} is a recognized {entity_type.lower()} who shares insights and opinions on important matters. They are known for their expertise and influence in public discourse.",
                "age": random.randint(35, 60),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(["ENTJ", "INTJ", "ENTP", "INTP"]),
                "country": random.choice(self.COUNTRIES),
                "profession": entity_attributes.get("occupation", "Expert"),
                "interested_topics": ["Politics", "Economics", "Culture & Society"],
            }
        
        elif entity_type_lower in ["mediaoutlet", "socialmediaplatform"]:
            return {
                "bio": f"Official account for {entity_name}. News and updates.",
                "persona": f"{entity_name} is a media entity that reports news and facilitates public discourse. The account shares timely updates and engages with the audience on current events.",
                "age": 30,  # Institutional virtual age
                "gender": "other",  # Institutions use 'other'
                "mbti": "ISTJ",  # Institutional style: Rigorous and conservative
                "country": "Unknown",
                "profession": "Media",
                "interested_topics": ["General News", "Current Events", "Public Affairs"],
            }
        
        elif entity_type_lower in ["university", "governmentagency", "ngo", "organization"]:
            return {
                "bio": f"Official account of {entity_name}.",
                "persona": f"{entity_name} is an institutional entity that communicates official positions, announcements, and engages with stakeholders on relevant matters.",
                "age": 30,  # Institutional virtual age
                "gender": "other",  # Institutions use 'other'
                "mbti": "ISTJ",  # Institutional style: Rigorous and conservative
                "country": "Unknown",
                "profession": entity_type,
                "interested_topics": ["Public Policy", "Community", "Official Announcements"],
            }

        # Default persona
            return {
                "bio": entity_summary[:150] if entity_summary else f"{entity_type}: {entity_name}",
                "persona": entity_summary or f"{entity_name} is a {entity_type.lower()} participating in social discussions.",
                "age": random.randint(25, 50),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(self.MBTI_TYPES),
                "country": random.choice(self.COUNTRIES),
                "profession": entity_type,
                "interested_topics": ["General", "Social Issues"],
            }
    
    def set_graph_id(self, graph_id: str):
        """Set graph ID for Zep retrieval"""
        self.graph_id = graph_id
    
    def generate_profiles_from_entities(
        self,
        entities: List[EntityNode],
        use_llm: bool = True,
        progress_callback: Optional[callable] = None,
        graph_id: Optional[str] = None,
        parallel_count: int = 5,
        realtime_output_path: Optional[str] = None,
        output_platform: str = "reddit"
    ) -> List[OasisAgentProfile]:
        """
        Batch generate Agent Profiles from entities (supports parallel generation)
        
        Supports checkpointing: if generation is interrupted, previously completed
        profiles are loaded from a checkpoint file on the next run, avoiding
        redundant LLM calls.
        
        Args:
            entities: Entity list
            use_llm: Whether to use LLM for detailed persona generation
            progress_callback: Progress callback function (current, total, message)
            graph_id: Graph ID, used for Zep retrieval to get richer context
            parallel_count: Parallel count, default 5
            realtime_output_path: Real-time output file path (if provided, write per generation)
            output_platform: Output platform format ("reddit" or "twitter")
            
        Returns:
            List of Agent Profiles
        """
        import concurrent.futures
        import os
        from threading import Lock
        
        # Set graph_id for Zep retrieval
        if graph_id:
            self.graph_id = graph_id
        
        total = len(entities)
        profiles = [None] * total  # Pre-allocate list to maintain order
        completed_count = [0]  # Use list for modification in closure
        lock = Lock()
        
        # ---- Checkpoint support ----
        checkpoint_path = None
        if realtime_output_path:
            checkpoint_dir = os.path.dirname(realtime_output_path)
            checkpoint_path = os.path.join(checkpoint_dir, ".profiles_checkpoint.json")
        
        # Load checkpoint if exists
        skipped_indices = set()
        if checkpoint_path and os.path.exists(checkpoint_path):
            try:
                with open(checkpoint_path, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                for entry in checkpoint_data:
                    idx = entry.get("user_id")
                    if idx is not None and idx < total:
                        profiles[idx] = OasisAgentProfile(
                            user_id=entry.get("user_id", idx),
                            user_name=entry.get("user_name", ""),
                            name=entry.get("name", ""),
                            bio=entry.get("bio", ""),
                            persona=entry.get("persona", ""),
                            karma=entry.get("karma", 1000),
                            friend_count=entry.get("friend_count", 100),
                            follower_count=entry.get("follower_count", 150),
                            statuses_count=entry.get("statuses_count", 500),
                            age=entry.get("age"),
                            gender=entry.get("gender"),
                            mbti=entry.get("mbti"),
                            country=entry.get("country"),
                            profession=entry.get("profession"),
                            interested_topics=entry.get("interested_topics", []),
                            source_entity_uuid=entry.get("source_entity_uuid"),
                            source_entity_type=entry.get("source_entity_type"),
                        )
                        skipped_indices.add(idx)
                        completed_count[0] += 1
                if skipped_indices:
                    logger.info(f"Checkpoint loaded: {len(skipped_indices)}/{total} profiles restored, resuming remaining")
            except Exception as e:
                logger.warning(f"Failed to load checkpoint, starting fresh: {e}")
                skipped_indices.clear()
                completed_count[0] = 0
                profiles = [None] * total
        
        def save_checkpoint():
            """Save completed profiles to checkpoint file"""
            if not checkpoint_path:
                return
            with lock:
                existing = [p.to_dict() for p in profiles if p is not None]
            try:
                with open(checkpoint_path, 'w', encoding='utf-8') as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Failed to write checkpoint: {e}")
        
        # Real-time save helper function
        def save_profiles_realtime():
            """Save generated profiles to file in real-time"""
            if not realtime_output_path:
                return
            
            with lock:
                # Filter generated profiles
                existing_profiles = [p for p in profiles if p is not None]
                if not existing_profiles:
                    return
                
                try:
                    if output_platform == "reddit":
                        # Reddit JSON format
                        profiles_data = [p.to_reddit_format() for p in existing_profiles]
                        with open(realtime_output_path, 'w', encoding='utf-8') as f:
                            json.dump(profiles_data, f, ensure_ascii=False, indent=2)
                    else:
                        # Twitter CSV format
                        import csv
                        profiles_data = [p.to_twitter_format() for p in existing_profiles]
                        if profiles_data:
                            fieldnames = list(profiles_data[0].keys())
                            with open(realtime_output_path, 'w', encoding='utf-8', newline='') as f:
                                writer = csv.DictWriter(f, fieldnames=fieldnames)
                                writer.writeheader()
                                writer.writerows(profiles_data)
                except Exception as e:
                    logger.warning(f"Failed to save profiles in real-time: {e}")
        
        def generate_single_profile(idx: int, entity: EntityNode) -> tuple:
            """Work function to generate single profile"""
            entity_type = entity.get_entity_type() or "Entity"
            
            try:
                profile = self.generate_profile_from_entity(
                    entity=entity,
                    user_id=idx,
                    use_llm=use_llm
                )
                
                # Print generated persona to console and log
                self._print_generated_profile(entity.name, entity_type, profile)
                
                return idx, profile, None
                
            except Exception as e:
                logger.error(f"Failed to generate persona for entity {entity.name}: {str(e)}")
                # Create fallback profile
                fallback_profile = OasisAgentProfile(
                    user_id=idx,
                    user_name=self._generate_username(entity.name),
                    name=entity.name,
                    bio=f"{entity_type}: {entity.name}",
                    persona=entity.summary or f"A participant in social discussions.",
                    source_entity_uuid=entity.uuid,
                    source_entity_type=entity_type,
                )
                return idx, fallback_profile, str(e)
        
        logger.info(f"Starting parallel generation of {total} Agent personas (parallel: {parallel_count})...")
        print(f"\n{'='*60}")
        print(f"Generating Agent personas - {total} entities total, parallel: {parallel_count}")
        print(f"{'='*60}\n")
        
        # Filter out already-checkpointed entities
        entities_to_process = [
            (idx, entity) for idx, entity in enumerate(entities)
            if idx not in skipped_indices
        ]
        
        if skipped_indices:
            print(f"  Checkpoint: {len(skipped_indices)} profiles restored, {len(entities_to_process)} remaining")
        
        # Parallel execution using thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_count) as executor:
            # Submit only non-checkpointed tasks
            future_to_entity = {
                executor.submit(generate_single_profile, idx, entity): (idx, entity)
                for idx, entity in entities_to_process
            }
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_entity):
                idx, entity = future_to_entity[future]
                entity_type = entity.get_entity_type() or "Entity"
                
                try:
                    result_idx, profile, error = future.result()
                    profiles[result_idx] = profile
                    
                    with lock:
                        completed_count[0] += 1
                        current = completed_count[0]
                    
                    # Write file in real-time and save checkpoint
                    save_profiles_realtime()
                    save_checkpoint()
                    
                    if progress_callback:
                        progress_callback(
                            current, 
                            total, 
                            f"Completed {current}/{total}: {entity.name} ({entity_type})"
                        )
                    
                    if error:
                        logger.warning(f"[{current}/{total}] {entity.name} using fallback persona: {error}")
                    else:
                        logger.info(f"[{current}/{total}] Successfully generated persona: {entity.name} ({entity_type})")
                        
                except Exception as e:
                    logger.error(f"Exception processing entity {entity.name}: {str(e)}")
                    with lock:
                        completed_count[0] += 1
                    profiles[idx] = OasisAgentProfile(
                        user_id=idx,
                        user_name=self._generate_username(entity.name),
                        name=entity.name,
                        bio=f"{entity_type}: {entity.name}",
                        persona=entity.summary or "A participant in social discussions.",
                        source_entity_uuid=entity.uuid,
                        source_entity_type=entity_type,
                    )
                    # Write file in real-time (even for fallback) and save checkpoint
                    save_profiles_realtime()
                    save_checkpoint()
        
        print(f"\n{'='*60}")
        print(f"Persona generation completed! Total {len([p for p in profiles if p])} Agents generated")
        print(f"{'='*60}\n")
        
        # Clean up checkpoint on successful completion
        if checkpoint_path and os.path.exists(checkpoint_path):
            try:
                os.remove(checkpoint_path)
                logger.debug("Checkpoint file cleaned up after successful completion")
            except Exception:
                pass
        
        return profiles
    
    def _print_generated_profile(self, entity_name: str, entity_type: str, profile: OasisAgentProfile):
        """Print generated persona to console (full content, NOT truncated)"""
        separator = "-" * 70
        
        # Build full output content
        topics_str = ', '.join(profile.interested_topics) if profile.interested_topics else 'None'
        
        output_lines = [
            f"\n{separator}",
            f"[Generated] {entity_name} ({entity_type})",
            f"{separator}",
            f"Username: {profile.user_name}",
            f"",
            f"[Bio]",
            f"{profile.bio}",
            f"",
            f"[Detailed Persona]",
            f"{profile.persona}",
            f"",
            f"[Attributes]",
            f"Age: {profile.age} | Gender: {profile.gender} | MBTI: {profile.mbti}",
            f"Profession: {profile.profession} | Country: {profile.country}",
            f"Interests: {topics_str}",
            separator
        ]
        
        output = "\n".join(output_lines)
        
        # Output to console only
        print(output)
    
    def save_profiles(
        self,
        profiles: List[OasisAgentProfile],
        file_path: str,
        platform: str = "reddit"
    ):
        """
        Save profiles to file (select correct format based on platform)
        
        OASIS platform format requirements:
        - Twitter: CSV format
        - Reddit: JSON format
        
        Args:
            profiles: Profile list
            file_path: File path
            platform: Platform type ("reddit" or "twitter")
        """
        if platform == "twitter":
            self._save_twitter_csv(profiles, file_path)
        else:
            self._save_reddit_json(profiles, file_path)
    
    def _save_twitter_csv(self, profiles: List[OasisAgentProfile], file_path: str):
        """
        Save Twitter profile as CSV format (OASIS official requirement)
        """
        import csv
        
        # Ensure file extension is .csv
        if not file_path.endswith('.csv'):
            file_path = file_path.replace('.json', '.csv')
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            headers = ['user_id', 'name', 'username', 'user_char', 'description']
            writer.writerow(headers)
            
            # Rows
            for idx, profile in enumerate(profiles):
                user_char = (profile.persona or profile.bio or profile.name).replace('\n', ' ').replace('\r', ' ')
                description = (profile.bio or profile.name).replace('\n', ' ').replace('\r', ' ')
                
                row = [
                    idx,
                    profile.name,
                    profile.user_name,
                    user_char,
                    description
                ]
                writer.writerow(row)
        
        logger.info(f"Saved {len(profiles)} Twitter profiles to {file_path} (OASIS CSV format)")
    
    def _normalize_gender(self, gender: Optional[str]) -> str:
        """
        Normalize gender field to OASIS required English format: male, female, other
        """
        if not gender:
            return "other"
        
        gender_lower = gender.lower().strip()
        
        # Mapping (supports both English and Chinese inputs)
        gender_map = {
            "male": "male",
            "female": "female",
            "other": "other",
            "man": "male",
            "woman": "female",
            "boy": "male",
            "girl": "female",
        }
        
        return gender_map.get(gender_lower, "other")
    
    def _save_reddit_json(self, profiles: List[OasisAgentProfile], file_path: str):
        """
        Save Reddit profiles as JSON format
        """
        data = []
        for profile in profiles:
            item = {
                "realname": profile.name,
                "username": profile.user_name,
                "bio": profile.bio[:150] if profile.bio else f"{profile.name}",
                "persona": profile.persona or f"{profile.name} is a participant in social discussions.",
                "age": profile.age if profile.age else 30,
                "gender": self._normalize_gender(profile.gender),
                "mbti": profile.mbti if profile.mbti else "ISTJ",
                "country": profile.country if profile.country else "Unknown",
            }
            if profile.profession:
                item["profession"] = profile.profession
            if profile.interested_topics:
                item["interested_topics"] = profile.interested_topics
            data.append(item)
 
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
 
        logger.info(f"Saved {len(profiles)} Reddit profiles to {file_path} (JSON format)")
    
    # Keep old method name as alias for backward compatibility
    def save_profiles_to_json(
        self,
        profiles: List[OasisAgentProfile],
        file_path: str,
        platform: str = "reddit"
    ):
        """[Deprecated] Please use save_profiles() method"""
        logger.warning("save_profiles_to_json is deprecated, please use save_profiles method")
        self.save_profiles(profiles, file_path, platform)
