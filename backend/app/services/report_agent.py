"""
Report Agent Service
Using Zep-backed retrieval to implement ReACT-mode synthetic scenario reporting

Features:
1. Generate scenario reports based on simulation requirements and Zep graph info
2. Plan directory structure first, then generate segment by segment
3. Each segment uses ReACT multi-round thinking and reflection
4. Support chat with users, autonomously calling retrieval tools during chat
"""

import os
import json
import time
import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..utils.safe_path import safe_join
from .report_generation_coordinator import (
    ReportGenerationCancelled,
    ReportGenerationLease,
)
from .report_evidence import build_report_evidence
from .claim_boundary import synthetic_output_disclosure
from .simulation_observation_store import search_observations
from .zep_tools import (
    ZepToolsService, 
    SearchResult, 
    InsightForgeResult, 
    PanoramaResult,
    InterviewResult
)

logger = get_logger('askthepeople.report_agent')

SYNTHETIC_REPORT_DISCLOSURE = (
    "**Human respondents: 0. Evidence type: synthetic.** "
    "This report describes possible paths generated inside a model-driven "
    "scenario. It is not a survey, measure of public opinion, forecast, "
    "prediction, causal estimate, or calibrated statement of likelihood. "
    "Validate consequential assumptions with real people and fit-for-purpose "
    "external evidence."
)
GRAPH_RETRIEVAL_PROVENANCE_NOTICE = (
    "[PROVENANCE: GRAPH_RECORD_ORIGIN_UNVERIFIED] These records came from the "
    "project graph. Record-level source versus generated origin is not "
    "verified; do not cite them as supplied-source facts without an independent "
    "source trace.\n\n"
)
OBSERVATION_RETRIEVAL_PROVENANCE_NOTICE = (
    "[PROVENANCE: SYNTHETIC_OBSERVATION] These records were generated inside "
    "this simulation run. Human respondents: 0. They are not source evidence "
    "or observed behavior.\n\n"
)


class ReportLogger:
    """
    Report Agent Detailed Logger
    
    Generate agent_log.jsonl in the report folder to record each detailed action.
    Each line is a complete JSON object including timestamp, action type, details, etc.
    """
    
    def __init__(
        self,
        report_id: str,
        generation_lease: ReportGenerationLease | None = None,
    ):
        """
        Initialize logger

        Args:
            report_id: Report ID, used to determine log file path
        """
        from ..utils.safe_path import safe_join
        self.report_id = report_id
        # Path-traversal defense: validate report_id before joining.
        reports_root = os.path.join(Config.UPLOAD_FOLDER, 'reports')
        report_folder = safe_join(reports_root, report_id)
        self.log_file_path = os.path.join(report_folder, 'agent_log.jsonl')
        self.start_time = datetime.now()
        self.generation_lease = generation_lease
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """Ensure log file directory exists"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _get_elapsed_time(self) -> float:
        """Get elapsed time from start (seconds)"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def log(
        self, 
        action: str, 
        stage: str,
        details: Dict[str, Any],
        section_title: str = None,
        section_index: int = None
    ):
        """
        Record a log entry
        
        Args:
            action: Action type, such as 'start', 'tool_call', 'llm_response', 'section_complete', etc.
            stage: Current stage, e.g., 'planning', 'generating', 'completed'
            details: Detailed content dictionary, not truncated
            section_title: Current section title (optional)
            section_index: Current section index (optional)
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(self._get_elapsed_time(), 2),
            "report_id": self.report_id,
            "action": action,
            "stage": stage,
            "section_title": section_title,
            "section_index": section_index,
            "details": details
        }
        
        def append_entry():
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        if self.generation_lease is None:
            append_entry()
        else:
            with self.generation_lease.write_guard():
                append_entry()
    
    def log_start(self, simulation_id: str, graph_id: str, simulation_requirement: str):
        """Record report generation start"""
        self.log(
            action="report_start",
            stage="pending",
            details={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "requirement_characters": len(simulation_requirement),
                "message": "Report generation task started"
            }
        )
    
    def log_planning_start(self):
        """Record outline planning start"""
        self.log(
            action="planning_start",
            stage="planning",
            details={"message": "Starting to plan report outline"}
        )
    
    def log_planning_context(self, context: Dict[str, Any]):
        """Record context info retrieved during planning"""
        self.log(
            action="planning_context",
            stage="planning",
            details={
                "message": "Retrieved simulation context info",
                "context_fields": sorted(str(key) for key in context.keys()),
            }
        )
    
    def log_planning_complete(self, outline_dict: Dict[str, Any]):
        """Record outline planning complete"""
        self.log(
            action="planning_complete",
            stage="planning",
            details={
                "message": "Outline planning complete",
                "outline": outline_dict
            }
        )
    
    def log_section_start(self, section_title: str, section_index: int):
        """Record section generation start"""
        self.log(
            action="section_start",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={"message": f"Starting to generate section: {section_title}"}
        )
    
    def log_react_thought(self, section_title: str, section_index: int, iteration: int, thought: str):
        """Record progress metadata without retaining model chain-of-thought."""
        self.log(
            action="react_thought",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "thought_characters": len(thought),
                "message": f"ReACT round {iteration} thinking"
            }
        )
    
    def log_tool_call(
        self, 
        section_title: str, 
        section_index: int,
        tool_name: str, 
        parameters: Dict[str, Any],
        iteration: int
    ):
        """Record a tool event without retaining user/source-derived values."""
        self.log(
            action="tool_call",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "parameter_names": sorted(str(key) for key in parameters.keys()),
                "message": f"Calling tool: {tool_name}"
            }
        )
    
    def log_tool_result(
        self,
        section_title: str,
        section_index: int,
        tool_name: str,
        result: str,
        iteration: int
    ):
        """Record tool completion metadata without duplicating retrieved data."""
        self.log(
            action="tool_result",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "result_length": len(result),
                "message": f"Tool {tool_name} returned results"
            }
        )
    
    def log_llm_response(
        self,
        section_title: str,
        section_index: int,
        response: str,
        iteration: int,
        has_tool_calls: bool,
        has_final_answer: bool
    ):
        """Record response metadata; final report text is stored separately."""
        self.log(
            action="llm_response",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "response_length": len(response),
                "has_tool_calls": has_tool_calls,
                "has_final_answer": has_final_answer,
                "message": f"LLM response (tool calls: {has_tool_calls}, final answer: {has_final_answer})"
            }
        )
    
    def log_section_content(
        self,
        section_title: str,
        section_index: int,
        content: str,
        tool_calls_count: int
    ):
        """Record section content generation complete (content only, not entire section)"""
        self.log(
            action="section_content",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": content,  # Full content, not truncated
                "content_length": len(content),
                "tool_calls_count": tool_calls_count,
                "message": f"Section {section_title} content generation complete"
            }
        )
    
    def log_section_full_complete(
        self,
        section_title: str,
        section_index: int,
        full_content: str
    ):
        """
        Record section generation complete

        Frontend should monitor this log to determine if a section is truly complete and get the full content.
        """
        self.log(
            action="section_complete",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": full_content,
                "content_length": len(full_content),
                "message": f"Section {section_title} generation complete"
            }
        )
    
    def log_report_complete(self, total_sections: int, total_time_seconds: float):
        """Record report generation complete"""
        self.log(
            action="report_complete",
            stage="completed",
            details={
                "total_sections": total_sections,
                "total_time_seconds": round(total_time_seconds, 2),
                "message": "Report generation complete"
            }
        )
    
    def log_error(self, error_message: str, stage: str, section_title: str = None):
        """Record a safe error event without provider/private response text."""
        self.log(
            action="error",
            stage=stage,
            section_title=section_title,
            section_index=None,
            details={
                "error_type": "report_generation_error",
                "error_characters": len(error_message),
                "message": "Report generation failed; private details omitted"
            }
        )


class ReportConsoleLogger:
    """
    Report Agent Console Logger
    
    Write console-style logs (INFO, WARNING, etc.) into console_log.txt in the report folder.
    These logs are different from agent_log.jsonl; they are plain text console output.
    """
    
    def __init__(self, report_id: str):
        """
        Initialize console logger
        
        Args:
            report_id: Report ID, used to determine log file path
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'console_log.txt'
        )
        self._ensure_log_file()
        self._file_handler = None
        self._setup_file_handler()
    
    def _ensure_log_file(self):
        """Ensure log file directory exists"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _setup_file_handler(self):
        """Set up file handler to write logs to file simultaneously"""
        import logging
        
        # Create file handler
        self._file_handler = logging.FileHandler(
            self.log_file_path,
            mode='a',
            encoding='utf-8'
        )
        self._file_handler.setLevel(logging.INFO)
        
        # Use the same concise format as the console
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        self._file_handler.setFormatter(formatter)
        
        # Add to report_agent related loggers
        loggers_to_attach = [
            'askthepeople.report_agent',
            'askthepeople.zep_tools',
        ]
        
        for logger_name in loggers_to_attach:
            target_logger = logging.getLogger(logger_name)
            # Avoid duplicate additions
            if self._file_handler not in target_logger.handlers:
                target_logger.addHandler(self._file_handler)
    
    def close(self):
        """Close file handler and remove from loggers"""
        import logging
        
        if self._file_handler:
            loggers_to_detach = [
                'askthepeople.report_agent',
                'askthepeople.zep_tools',
            ]
            
            for logger_name in loggers_to_detach:
                target_logger = logging.getLogger(logger_name)
                if self._file_handler in target_logger.handlers:
                    target_logger.removeHandler(self._file_handler)
            
            self._file_handler.close()
            self._file_handler = None
    
    def __del__(self):
        """Ensure file handler is closed upon destruction"""
        self.close()


class ReportStatus(str, Enum):
    """Report status"""
    PENDING = "pending"
    PLANNING = "planning"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReportSection:
    """Report section"""
    title: str
    content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "truth_status": synthetic_output_disclosure(),
        }

    def to_markdown(self, level: int = 2) -> str:
        """Convert to Markdown format"""
        md = f"{'#' * level} {self.title}\n\n"
        if self.content:
            md += f"{self.content}\n\n"
        return md


@dataclass
class ReportOutline:
    """Report outline"""
    title: str
    summary: str
    sections: List[ReportSection]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "sections": [s.to_dict() for s in self.sections],
            "truth_status": synthetic_output_disclosure(),
        }
    
    def to_markdown(self) -> str:
        """Convert to Markdown format"""
        md = f"# {self.title}\n\n"
        md += f"> {self.summary}\n\n"
        md += f"> {SYNTHETIC_REPORT_DISCLOSURE}\n\n"
        for section in self.sections:
            md += section.to_markdown()
        return md


@dataclass
class Report:
    """Full report"""
    report_id: str
    simulation_id: str
    graph_id: str
    simulation_requirement: str
    status: ReportStatus
    outline: Optional[ReportOutline] = None
    markdown_content: str = ""
    created_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "simulation_id": self.simulation_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "status": self.status.value,
            "outline": self.outline.to_dict() if self.outline else None,
            "markdown_content": self.markdown_content,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "truth_status": synthetic_output_disclosure(),
        }


# ===============================================================
# Prompt Template Constants
# ===============================================================

# -- Tool Descriptions --

TOOL_DESC_INSIGHT_FORGE = """\
[Deep Insight Search - Powerful Retrieval Tool]
This is our most powerful retrieval function, designed for in-depth analysis. It will:
1. Automatically decompose your query into multiple sub-queries.
2. Retrieve information from the project graph across multiple dimensions.
3. Integrate results from semantic search, entity analysis, and relationship chain tracking.
4. Return the most comprehensive and in-depth retrieval content.

[Usage Scenarios]
- Need in-depth analysis of a specific topic.
- Need to understand multiple aspects of an event.
- Need to acquire rich material to support report sections.

[Returned Content]
- Graph records that may be source-derived, inferred, or generated.
- Core entity insights.
- Relationship chain analysis.

[Interpretation Boundary]
- Call something a source fact only when its provenance identifies the supplied source.
- Label generated or simulation-updated records as synthetic observations.
- If provenance is unclear, say so; retrieval does not verify real-world truth."""

TOOL_DESC_PANORAMA_SEARCH = """\
[Panorama Search - Get the Full Picture]
This tool provides a broad view of records currently held in the project graph. It will:
1. Retrieve all relevant nodes and relationships.
2. Distinguish between currently active facts and historical/expired facts.
3. Show graph structure without asserting record-level provenance.

[Usage Scenarios]
- Need to understand graph relationships around an event.
- Need to compare active and expired graph records.
- Need to acquire comprehensive entity and relationship information.

[Returned Content]
- Currently active graph records.
- Historical/expired graph records.
- Involved graph entities.

[Interpretation Boundary]
Record-level origin is unverified. Do not treat these as supplied-source facts,
simulation observations, public-opinion data, or human responses without a
separate provenance trace."""

TOOL_DESC_QUICK_SEARCH = """\
[Quick Search - Fast Retrieval]
A lightweight fast retrieval tool, suitable for simple and direct information queries.

[Usage Scenarios]
- Need to quickly find a specific piece of information.
- Need to locate a specific graph record.
- Simple information retrieval.

[Returned Content]
- A list of graph records most relevant to the query.

[Interpretation Boundary]
Retrieval can confirm that a record exists in the project graph. It cannot
independently verify that the record is true in the real world."""

TOOL_DESC_SIMULATION_OBSERVATIONS = """\
[Synthetic Observation Search]
Searches the per-run observation store for generated action records.

[Usage Scenarios]
- Inspect what generated actors said or did within this run.
- Compare generated activity across platforms or rounds.
- Locate a keyword-related generated excerpt for run inspection; never label it
  a citation or independent support for a report statement.

[Interpretation Boundary]
Every returned record is a synthetic observation or configuration assumption.
Human respondents: 0. These records are not supplied-source facts, observed
behavior, public opinion, validation, or forecasts."""

TOOL_DESC_INTERVIEW_AGENTS = """\
[Fictional Generated-Profile Follow-up]
Asks fictional profiles in the OASIS environment a follow-up question. Every
answer is another model output. No person is recruited, sampled, observed, or
interviewed. By default, the same question is asked in both fictional channel
contexts; this does not make the answer more representative or reliable.

Functional Flow:
1. Reads generated profile assumptions for the configured run.
2. Selects profile records using run labels and the requested topic.
3. Generates follow-up questions.
4. Calls the /api/simulation/generated-response/batch compatibility interface.
5. Collects the fictional responses without converting them into human evidence.

[Usage Scenarios]
- Explore how generated roles respond under the configured assumptions.
- Generate possible viewpoints to test later with real people.
- Inspect model behavior inside the OASIS environment.

[Returned Content]
- Synthetic persona information.
- Generated responses on Twitter-like and Reddit-like environments.
- Generated excerpts, which must be labeled as such.
- A comparison of generated viewpoints.

[IMPORTANT]
Requires the OASIS simulation environment to be running. These results must
never be described as human interviews, respondents, testimony, public opinion,
or validation."""

# -- Outline Planning Prompt --

PLAN_SYSTEM_PROMPT = """\
You write synthetic scenario-exploration reports. You can inspect the generated
behavior, speech, and interactions of every synthetic Agent in one configured
simulation run.

[Non-Negotiable Truth Boundary]
- Human respondents: 0.
- Agents, posts, comments, actions, and interviews are generated, not observed people.
- The run is not a survey, focus group, measure of public opinion, forecast,
  prediction, causal estimate, digital twin, or calibrated likelihood model.
- A large synthetic population is not a representative sample.
- Generated consistency, frequency, or metrics do not establish real-world
  probability, prevalence, confidence, or evidence strength.
- Refer to "possible paths," "generated actors," and "within this run."
- Never write that people, the public, or a demographic group will believe or do
  something. Instead write that a generated persona did something and turn it
  into a hypothesis to validate with real people.

[Evidence Classes]
Keep these separate:
1. Source facts: statements traceable to supplied source material. Their factual
   status may still require independent verification.
2. Configuration assumptions: injected events, prompts, personas, and platform rules.
3. Synthetic observations: generated actions and statements inside this run.
4. Internal metrics: descriptions of generated activity only.
5. Model interpretations: narrative synthesis of the above.
6. External human or behavioral evidence: none unless separately supplied and
   documented; do not invent it.
If provenance is unclear, state "origin unclear" rather than upgrading a record
to a source fact.

[Your Task]
Create a concise scenario report that:
1. Restates the decision, source basis, and important assumptions.
2. Maps multiple possible paths without ranking them by likelihood.
3. Describes what emerged inside this run, including platform differences.
4. Makes uncertainty, missing stakeholders, weak support, and contradictions visible.
5. Converts paths into questions and evidence needs for real-human validation.

[Required Sections]
- Decision, Sources, and Assumptions
- Possible Scenario Paths
- Platform Divergence
- Uncertainty and Missing Evidence
- Validate with People

Please output the report outline in JSON format as follows:
{
    "title": "Synthetic Scenario Exploration: [Decision]",
    "summary": "One sentence naming possible paths and emphasizing that this is one synthetic run, not a forecast.",
    "sections": [
        {
            "title": "Section Title",
            "description": "Section Content Description"
        }
    ]
}

Return exactly the five required sections. Do not use prediction, forecast,
confidence, likelihood, public-opinion, or human-response language."""

PLAN_USER_PROMPT_TEMPLATE = """\
[Scenario Question and Injected Conditions]
{simulation_requirement}

[Generated Run Scale - Not a Human Sample]
- Graph entities used by the scenario: {total_nodes}
- Graph relationships used by the scenario: {total_edges}
- Entity type distribution: {entity_types}
- Generated active Agents: {total_entities}
- Human respondents: 0

[Retrieved Graph Records - Record-Level Origin Unverified]
Do not classify a record as a supplied-source fact unless a separate source
trace proves that origin. Older graphs may contain mixed records.
{related_facts_json}

Plan a report about possible paths produced within this synthetic run. Do not
infer prevalence, probability, representation, causality, or future human
behavior. Return exactly the five required sections."""

# -- Section Generation Prompt --

SECTION_SYSTEM_PROMPT_TEMPLATE = """\
You are writing one section of a synthetic scenario-exploration report.

Report Title: {report_title}
Report Summary: {report_summary}
Scenario Question and Injected Conditions: {simulation_requirement}

Current Section to write: {section_title}

===============================================================
[Truth Boundary]
===============================================================

- Human respondents: 0.
- Every Agent statement and action is generated inside a configured run.
- The report is not a forecast, prediction, survey, public-opinion analysis,
  causal estimate, or statement of likelihood.
- Do not call synthetic Agents people, populations, participants, respondents,
  interviewees, the public, consumers, voters, residents, or other real groups.
- Do not turn generated counts into prevalence or probability.
- Use conditional language: "within this run," "one possible path," and "a
  hypothesis to validate."
- Do not contradict or dilute the disclosure inserted into the report header.

===============================================================
[Most Important Rules - Must Follow]
===============================================================

1. [Use Tools to Inspect the Synthetic Run]
   - All run-specific claims must come from retrieved records.
   - Forbidden to use your own knowledge to write report content
   - Call tools at least 3 times per section (maximum 5).

2. [Label Generated Excerpts]
   - Agent speech and behavior are synthetic observations.
   - Display excerpts as labeled generated records, for example:
     > Generated Agent 12: "generated content..."
   - Never attribute generated words to a real group or named person.

3. [Language Consistency - Labeled Excerpts Use the Report Language]
   - Content returned by tools may include English or mixed Chinese-English expressions.
   - Even if simulation requirements and original materials are in Chinese, the report must be written entirely in English for this localized version.
   - Ensure all labeled excerpts are in clear English. If a record is Chinese, translate it to English.
   - Maintain original meaning during translation, ensuring natural flow.
   - This rule applies to both the main text and labeled blockquotes (">" format).

4. [Separate Evidence Classes]
   - Clearly distinguish source facts, configuration assumptions, synthetic
     observations, internal metrics, and model interpretation.
   - A graph record is not automatically a verified source fact.
   - Do not add information that does not exist in the simulation
   - If provenance or support is lacking, state so truthfully.

5. [Write for Validation]
   - Describe multiple possible paths without ranking likelihood.
   - Name missing stakeholders and alternate explanations.
   - End with questions or external evidence needed from real people.

===============================================================
[[WARN] Formatting Specification - Extremely Important!]
===============================================================

[One Section = Minimum Content Unit]
- Each section is the smallest modular unit of the report
- [NO] Forbidden to use any Markdown headers (#, ##, ###, ####, etc.) within sections
- [NO] Forbidden to add a main section title at the beginning of the content
- [YES] Section titles are added automatically; you only need to write pure body text
- [YES] Use **bold**, paragraph breaks, citations, and lists to organize content, but do not use headers

[Correct Example]
```
Within this run, generated activity followed one path worth testing. This is not
a claim about how real people will respond.

**Generated trigger**

The Twitter-like environment carried the first generated post:

> Generated Agent 12: "generated content..."

**Validation need**

Interview affected people about whether this concern exists and what conditions
would change it.
```

[Error Example]
```
## Executive Summary          <-- Error! Do not add any headers
### I. Initial Phase     <-- Error! Do not use ### for sub-sections
#### 1.1 Detailed Analysis   <-- Error! Do not use #### for fine-tuning

This section analyzes...
```

===============================================================
[Available Retrieval Tools] (3-5 calls per section)
===============================================================

{tools_description}

[Tool Usage Suggestions - Please use a mix of different tools, do not rely on just one]
- insight_forge: Retrieve graph records and relationships across multiple dimensions.
- panorama_search: Inspect project-graph structure with unverified record-level provenance.
- quick_search: Locate a specific project-graph record.
- simulation_observations: Inspect generated run activity from the separate observation store.
- interview_agents: Generate responses from synthetic Agents; never human interviews.

===============================================================
[Workflow]
===============================================================

In each reply, you can only do one of the following two things (not both at once):

Option A - Call Tool:
Output your thoughts, then call a tool using the following format:
<tool_call>
{{"name": "tool_name", "parameters": {{"param_name": "param_value"}}}}
</tool_call>
The system will execute the tool and return the results to you. You do not need to and cannot write the tool results yourself.

Option B - Output Final Content:
When you have gathered enough information via tools, output the section content starting with "Final Answer:".

[WARN] Strictly prohibited:
- Forbidden to include both a tool call and Final Answer in a single reply
- Forbidden to make up tool results (Observation); all results are injected by the system
- Maximum one tool call per reply

===============================================================
[Section Content Requirements]
===============================================================

1. Run-specific content must be based on records retrieved via tools.
2. Use generated excerpts only when clearly labeled as generated; they are not citations.
3. Use Markdown format (but forbid using headers):
   - Use **bold text** to mark key points (instead of sub-headers)
   - Use lists (- or 1.2.3.) to organize points
   - Use blank lines to separate different paragraphs
   - [NO] Forbidden to use any header syntax like #, ##, ###, ####, etc.
4. [Labeled Excerpt Format - Must Be a Separate Paragraph]
   Labeled excerpts must be standalone paragraphs with an empty line before and after; do not mix them into text paragraphs:

   [YES] Correct Format:
   ```
   The university's response was considered lacking in substance.

   > "The university's response model appeared rigid and slow in the rapidly changing social media environment."

   This generated excerpt suggests a concern to test with affected people.
   ```

   [NO] Error Format:
   ```
   The university's response was considered lacking in substance.> "The university's response mode..." This evaluation reflects...
   ```
5. Maintain logical consistency with other sections
6. [Avoid Duplication] Read the completed section content below carefully to avoid repeating the same information
7. [Reiterate] Do not add any headers! Use **bold** instead of sub-headers"""

SECTION_USER_PROMPT_TEMPLATE = """\
Completed section content (read carefully to avoid duplication):
{previous_content}

===============================================================
[Current Task] Writing Section: {section_title}
===============================================================

[Important Reminders]
1. Read the completed sections above carefully to avoid repeating the same content!
2. Must call tools to gather simulation data before starting
3. Use a mix of different tools, do not rely on just one
4. Report content must come from retrieval results; do not use your own knowledge

[[WARN] Formatting Warning - Must Follow]
- [NO] Do not write any headers (#, ##, ###, #### are all disallowed)
- [NO] Do not write "{section_title}" as an opening
- [YES] Section titles are added automatically
- [YES] Write body text directly, using **bold** instead of sub-headers

Please start:
1. First, think (Thought) about what information this section needs
2. Then, call tools (Action) to gather simulation data
3. Output Final Answer (pure body text, no headers) after gathering sufficient information"""

# -- Messages for ReACT Loop --

REACT_OBSERVATION_TEMPLATE = """\
Observation (retrieval results):

=== Tool {tool_name} returned ===
{result}

===============================================================
Used tool {tool_calls_count}/{max_tool_calls} times (Used: {used_tools_str}) {unused_hint}
- If info is sufficient: Start with "Final Answer:" and output section content.
  Use an excerpt only when its provenance is explicit. Label synthetic excerpts
  as generated and graph text as origin-unverified; never present either as a
  supplied-source citation.
- If more info is needed: Call a tool to continue retrieval
==============================================================="""

REACT_INSUFFICIENT_TOOLS_MSG = (
    "[Note] You have only called tools {tool_calls_count} times; at least {min_tool_calls} are required."
    "Please call tools again to gather more simulation data before outputting Final Answer. {unused_hint}"
)

REACT_INSUFFICIENT_TOOLS_MSG_ALT = (
    "Currently called tools {tool_calls_count} times; at least {min_tool_calls} are required."
    "Please call tools to gather simulation data. {unused_hint}"
)

REACT_TOOL_LIMIT_MSG = (
    "Tool call limit reached ({tool_calls_count}/{max_tool_calls}); no more tool calls allowed."
    'Please immediately output section content starting with "Final Answer:" based on the information obtained.'
)

REACT_UNUSED_TOOLS_HINT = "\n[HINT] You haven't used: {unused_list} yet; it's recommended to try different tools for multi-perspective info"

REACT_FORCE_FINAL_MSG = "Tool call limit reached; please output Final Answer: and generate section content directly."

# -- Chat prompt --

CHAT_SYSTEM_PROMPT_TEMPLATE = """\
You are a concise synthetic scenario-exploration assistant.

[Background]
Scenario Question and Injected Conditions: {simulation_requirement}

[Generated Analysis Report]
{report_content}

[Rules]
1. Human respondents: 0; all Agent behavior and interviews are generated.
2. Never present the report as a survey, public opinion, forecast, prediction,
   probability, causal estimate, or real-human response.
3. Distinguish source facts, assumptions, synthetic observations, internal
   metrics, and model interpretations.
4. Use "within this run" and "possible path"; identify what needs validation with real people.
5. Prioritize the report, call tools only when needed, and answer directly.

[Available Tools] (Only use as needed, maximum 1-2 calls)
{tools_description}

[Tool Call Format]
<tool_call>
{{"name": "tool_name", "parameters": {{"param_name": "param_value"}}}}
</tool_call>

[Response Style]
- Concise and direct, no long-windedness
- Use > format to cite key content
- Give conclusions first, then explain reasons"""

CHAT_OBSERVATION_SUFFIX = "\n\nPlease answer the question concisely."


# ===============================================================
# ReportAgent Main Class
# ===============================================================


class ReportAgent:
    """
    Report Agent - Simulated Report Generation Agent

    Uses ReACT (Reasoning + Acting) pattern:
    1. Planning phase: Analyze Simulation requirement, plan report directory structure
    2. Generation phase: Generate content chapter by chapter; each chapter can call tools multiple times
    3. Reflection phase: Check content completeness and accuracy
    """
    
    # Max tool calls per section
    MAX_TOOL_CALLS_PER_SECTION = 5
    
    # Max reflection rounds
    MAX_REFLECTION_ROUNDS = 3
    
    # Max tool calls in chat
    MAX_TOOL_CALLS_PER_CHAT = 2
    REQUIRED_SECTION_TITLES = [
        "Decision, Sources, and Assumptions",
        "Possible Scenario Paths",
        "Platform Divergence",
        "Uncertainty and Missing Evidence",
        "Validate with People",
    ]
    
    def __init__(
        self, 
        graph_id: str,
        simulation_id: str,
        simulation_requirement: str,
        llm_client: Optional[LLMClient] = None,
        zep_tools: Optional[ZepToolsService] = None
    ):
        """
        Initialize Report Agent
        
        Args:
            graph_id: Graph ID
            simulation_id: Simulation ID
            simulation_requirement: Simulation requirement description
            llm_client: LLM client (optional)
            zep_tools: Zep tools service (optional)
        """
        self.graph_id = graph_id
        self.simulation_id = simulation_id
        self.simulation_requirement = simulation_requirement

        self.llm = llm_client or LLMClient(prefer_boost=True)
        self.zep_tools = zep_tools or ZepToolsService()

        # Tool definitions
        self.tools = self._define_tools()

        # Report Logger (initialized in generate_report)
        self.report_logger: Optional[ReportLogger] = None
        # Console Logger (initialized in generate_report)
        self.console_logger: Optional[ReportConsoleLogger] = None
        self._generation_lease: ReportGenerationLease | None = None

        # Load pre-computed simulation metrics (may be None if not yet computed)
        try:
            from .validation_engine import ValidationEngine
            self._simulation_metrics: Optional[Dict[str, Any]] = ValidationEngine.load_metrics(simulation_id)
        except Exception:
            self._simulation_metrics = None

        logger.info(f"ReportAgent initialized: graph_id={graph_id}, simulation_id={simulation_id}")

    def _generation_checkpoint(self) -> None:
        if self._generation_lease is not None:
            self._generation_lease.checkpoint()

    def _generation_write_guard(self):
        if self._generation_lease is not None:
            return self._generation_lease.write_guard()
        from contextlib import nullcontext

        return nullcontext()
    
    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        """Define available tools"""
        return {
            "insight_forge": {
                "name": "insight_forge",
                "description": TOOL_DESC_INSIGHT_FORGE,
                "parameters": {
                    "query": "The question or topic you want to analyze deeply",
                    "report_context": "Context of the current Report section (optional, helps generate more accurate sub-queries)"
                }
            },
            "panorama_search": {
                "name": "panorama_search",
                "description": TOOL_DESC_PANORAMA_SEARCH,
                "parameters": {
                    "query": "Search query for relevance sorting",
                    "include_expired": "Whether to include expired/historical content (default True)"
                }
            },
            "quick_search": {
                "name": "quick_search",
                "description": TOOL_DESC_QUICK_SEARCH,
                "parameters": {
                    "query": "Search query string",
                    "limit": "Number of results to return (optional, default 10)"
                }
            },
            "simulation_observations": {
                "name": "simulation_observations",
                "description": TOOL_DESC_SIMULATION_OBSERVATIONS,
                "parameters": {
                    "query": "Text to find in generated action records",
                    "platform": "Optional twitter or reddit filter",
                    "agent_id": "Optional generated Agent ID",
                    "limit": "Number of results to return (optional, default 20, max 50)",
                },
            },
            "interview_agents": {
                "name": "interview_agents",
                "description": TOOL_DESC_INTERVIEW_AGENTS,
                "parameters": {
                    "interview_topic": "Interview topic or requirement description (e.g., 'Understand student views on dorm formaldehyde event')",
                    "max_agents": "Maximum number of Agents to interview (optional, default 5, max 10)"
                }
            }
        }
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any], report_context: str = "") -> str:
        """
        Execute tool call
        
        Args:
            tool_name: Tool name
            parameters: Tool parameters
            report_context: Report context (for InsightForge)
            
        Returns:
            Tool execution result (text format)
        """
        logger.info(
            "Executing report tool: %s (parameter_names=%s)",
            tool_name,
            sorted(str(key) for key in parameters),
        )
        
        try:
            if tool_name == "insight_forge":
                query = parameters.get("query", "")
                ctx = parameters.get("report_context", "") or report_context
                result = self.zep_tools.insight_forge(
                    graph_id=self.graph_id,
                    query=query,
                    simulation_requirement=self.simulation_requirement,
                    report_context=ctx
                )
                self._generation_checkpoint()
                return GRAPH_RETRIEVAL_PROVENANCE_NOTICE + result.to_text()
            
            elif tool_name == "panorama_search":
                # Broad search - get full picture
                query = parameters.get("query", "")
                include_expired = parameters.get("include_expired", True)
                if isinstance(include_expired, str):
                    include_expired = include_expired.lower() in ['true', '1', 'yes']
                result = self.zep_tools.panorama_search(
                    graph_id=self.graph_id,
                    query=query,
                    include_expired=include_expired
                )
                self._generation_checkpoint()
                return GRAPH_RETRIEVAL_PROVENANCE_NOTICE + result.to_text()
            
            elif tool_name == "quick_search":
                # Simple search - quick retrieval
                query = parameters.get("query", "")
                limit = parameters.get("limit", 10)
                if isinstance(limit, str):
                    limit = int(limit)
                result = self.zep_tools.quick_search(
                    graph_id=self.graph_id,
                    query=query,
                    limit=limit
                )
                self._generation_checkpoint()
                return GRAPH_RETRIEVAL_PROVENANCE_NOTICE + result.to_text()

            elif tool_name == "simulation_observations":
                limit = parameters.get("limit", 20)
                try:
                    limit = int(limit)
                except (TypeError, ValueError):
                    limit = 20
                agent_id = parameters.get("agent_id")
                if agent_id not in (None, ""):
                    try:
                        agent_id = int(agent_id)
                    except (TypeError, ValueError):
                        raise ValueError("agent_id must be an integer")
                else:
                    agent_id = None
                result = search_observations(
                    safe_join(
                        Config.OASIS_SIMULATION_DATA_DIR,
                        self.simulation_id,
                    ),
                    query=parameters.get("query", ""),
                    platform=parameters.get("platform") or None,
                    agent_id=agent_id,
                    limit=limit,
                )
                for record in result.get("results", []):
                    record["evidence_class"] = "synthetic_observation"
                    record["human_respondents"] = 0
                    record["external_validation"] = False
                self._generation_checkpoint()
                return (
                    OBSERVATION_RETRIEVAL_PROVENANCE_NOTICE
                    + json.dumps(result, ensure_ascii=False, indent=2)
                )
            
            elif tool_name == "interview_agents":
                # Deep interview - call real OASIS interview API to get simulated Agent answers (dual platform)
                interview_topic = parameters.get("interview_topic", parameters.get("query", ""))
                max_agents = parameters.get("max_agents", 5)
                if isinstance(max_agents, str):
                    max_agents = int(max_agents)
                max_agents = min(max_agents, 10)
                result = self.zep_tools.interview_agents(
                    simulation_id=self.simulation_id,
                    interview_requirement=interview_topic,
                    simulation_requirement=self.simulation_requirement,
                    max_agents=max_agents
                )
                self._generation_checkpoint()
                return OBSERVATION_RETRIEVAL_PROVENANCE_NOTICE + result.to_text()
            
            # ========== Backward compatible old tools (internally redirected to new tools) ==========
            
            elif tool_name == "search_graph":
                # Redirected to quick_search
                logger.info("search_graph redirected to quick_search")
                return self._execute_tool("quick_search", parameters, report_context)
            
            elif tool_name == "get_graph_statistics":
                result = self.zep_tools.get_graph_statistics(self.graph_id)
                self._generation_checkpoint()
                return (
                    GRAPH_RETRIEVAL_PROVENANCE_NOTICE
                    + json.dumps(result, ensure_ascii=False, indent=2)
                )
            
            elif tool_name == "get_entity_summary":
                entity_name = parameters.get("entity_name", "")
                result = self.zep_tools.get_entity_summary(
                    graph_id=self.graph_id,
                    entity_name=entity_name
                )
                self._generation_checkpoint()
                return (
                    GRAPH_RETRIEVAL_PROVENANCE_NOTICE
                    + json.dumps(result, ensure_ascii=False, indent=2)
                )
            
            elif tool_name == "get_simulation_context":
                # Redirect to insight_forge as it's more powerful
                logger.info("get_simulation_context redirected to insight_forge")
                query = parameters.get("query", self.simulation_requirement)
                return self._execute_tool("insight_forge", {"query": query}, report_context)
            
            elif tool_name == "get_entities_by_type":
                entity_type = parameters.get("entity_type", "")
                nodes = self.zep_tools.get_entities_by_type(
                    graph_id=self.graph_id,
                    entity_type=entity_type
                )
                result = [n.to_dict() for n in nodes]
                self._generation_checkpoint()
                return (
                    GRAPH_RETRIEVAL_PROVENANCE_NOTICE
                    + json.dumps(result, ensure_ascii=False, indent=2)
                )
            
            else:
                return (
                    f"Unknown tool: {tool_name}. Please use one of the following: "
                    "insight_forge, panorama_search, quick_search, "
                    "simulation_observations, interview_agents"
                )
                
        except ReportGenerationCancelled:
            raise
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}, error: {str(e)}")
            return f"Tool execution failed: {str(e)}"
    
    # Valid tool names set, used for validation during bare JSON parsing
    VALID_TOOL_NAMES = {
        "insight_forge",
        "panorama_search",
        "quick_search",
        "simulation_observations",
        "interview_agents",
    }

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse tool calls from LLM response

        Supported formats (by priority):
        1. <tool_call>{"name": "tool_name", "parameters": {...}}</tool_call>
        2. Bare JSON (the whole response or a single line is a tool call JSON)
        """
        tool_calls = []

        # Format 1: XML style (standard format)
        xml_pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        for match in re.finditer(xml_pattern, response, re.DOTALL):
            try:
                call_data = json.loads(match.group(1))
                tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        if tool_calls:
            return tool_calls

        # Format 2: Fallback - LLM directly outputs bare JSON (not wrapped in <tool_call> tags)
        # Only try if Format 1 didn't match to avoid mis-matching JSON in body text
        stripped = response.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            try:
                call_data = json.loads(stripped)
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
                    return tool_calls
            except json.JSONDecodeError:
                pass

        # Response might contain thoughts + bare JSON, try to extract last JSON object
        json_pattern = r'(\{"(?:name|tool)"\s*:.*?\})\s*$'
        match = re.search(json_pattern, stripped, re.DOTALL)
        if match:
            try:
                call_data = json.loads(match.group(1))
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        return tool_calls

    def _is_valid_tool_call(self, data: dict) -> bool:
        """Validate if the parsed JSON is a legal tool call"""
        # Supports both {"name": ..., "parameters": ...} and {"tool": ..., "params": ...} key names
        tool_name = data.get("name") or data.get("tool")
        if tool_name and tool_name in self.VALID_TOOL_NAMES:
            # Unify keys to name / parameters
            if "tool" in data:
                data["name"] = data.pop("tool")
            if "params" in data and "parameters" not in data:
                data["parameters"] = data.pop("params")
            return True
        return False
    
    def _get_tools_description(self) -> str:
        """Generate tool description text"""
        desc_parts = ["Available Tools:"]
        for name, tool in self.tools.items():
            params_desc = ", ".join([f"{k}: {v}" for k, v in tool["parameters"].items()])
            desc_parts.append(f"- {name}: {tool['description']}")
            if params_desc:
                desc_parts.append(f"  Params: {params_desc}")
        return "\n".join(desc_parts)

    def _normalize_section_title(self, title: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", (title or "").lower())

    def _ensure_required_outline_sections(self, outline: ReportOutline) -> ReportOutline:
        existing_by_title = {
            self._normalize_section_title(section.title): section
            for section in outline.sections
        }
        outline.sections = [
            existing_by_title.get(
                self._normalize_section_title(title),
                ReportSection(title=title),
            )
            for title in self.REQUIRED_SECTION_TITLES
        ]
        return outline
    
    def plan_outline(
        self, 
        progress_callback: Optional[Callable] = None
    ) -> ReportOutline:
        """
        Plan Report outline
        
        Use LLM to analyze Simulation requirement and plan report directory structure
        
        Args:
            progress_callback: Progress callback function
            
        Returns:
            ReportOutline: Report outline
        """
        logger.info("Starting report outline planning...")
        
        if progress_callback:
            progress_callback("planning", 0, "Analyzing Simulation requirement...")
        
        # Get simulation context first
        context = self.zep_tools.get_simulation_context(
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement
        )
        self._generation_checkpoint()
        
        if progress_callback:
            progress_callback("planning", 30, "Generating Report outline...")
        
        system_prompt = PLAN_SYSTEM_PROMPT
        user_prompt = PLAN_USER_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            total_nodes=context.get('graph_statistics', {}).get('total_nodes', 0),
            total_edges=context.get('graph_statistics', {}).get('total_edges', 0),
            entity_types=list(context.get('graph_statistics', {}).get('entity_types', {}).keys()),
            total_entities=context.get('total_entities', 0),
            related_facts_json=json.dumps(context.get('related_facts', [])[:10], ensure_ascii=False, indent=2),
        )

        if self._simulation_metrics:
            m = self._simulation_metrics
            user_prompt = user_prompt + (
                "\n\n## Within-Run Generated Interaction Metrics\n"
                "These are descriptive calculations over synthetic actions, not "
                "measurements of people, external validation, or calibrated evidence.\n"
                f"- Network modularity Q (implementation labels this polarization): "
                f"{m.get('polarization_index', 0):.3f}\n"
                f"- Gini of generated action counts: "
                f"{m.get('engagement_gini', 0):.3f}\n"
                f"- Within-community share of generated interaction edges: "
                f"{m.get('echo_chamber_score', 0):.3f}\n"
                f"- Generated communities detected: {m.get('community_count', 'N/A')}\n"
                f"- Generated actions counted: {m.get('total_actions', 0)}\n"
            )

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            self._generation_checkpoint()
            
            if progress_callback:
                progress_callback("planning", 80, "Parsing outline structure...")
            
            # Parse outline
            sections = []
            for section_data in response.get("sections", []):
                sections.append(ReportSection(
                    title=section_data.get("title", ""),
                    content=""
                ))
            
            outline = ReportOutline(
                title=response.get("title", "Simulation Analysis Report"),
                summary=response.get("summary", ""),
                sections=sections
            )
            outline = self._ensure_required_outline_sections(outline)
            
            if progress_callback:
                progress_callback("planning", 100, "Outline planning complete")
            
            logger.info(f"Outline planning complete: {len(outline.sections)} sections")
            return outline
            
        except ReportGenerationCancelled:
            raise
        except Exception as e:
            logger.error(f"Outline planning failed: {str(e)}")
            # Return a truth-preserving default outline.
            return self._ensure_required_outline_sections(ReportOutline(
                title="Synthetic Scenario Exploration Report",
                summary=(
                    "Possible paths from one synthetic run; 0 human respondents "
                    "and not a forecast."
                ),
                sections=[],
            ))
    
    def _generate_section_react(
        self, 
        section: ReportSection,
        outline: ReportOutline,
        previous_sections: List[str],
        progress_callback: Optional[Callable] = None,
        section_index: int = 0
    ) -> str:
        """
        Generate single section content using ReACT pattern
        
        ReACT cycle:
        1. Thought - Analyze what information is needed
        2. Action - Call tool to gather information
        3. Observation - Analyze tool output
        4. Repeat until information is sufficient or max iterations reached
        5. Final Answer - Generate section content
        
        Args:
            section: Section to generate
            outline: Full outline
            previous_sections: Content of previous sections (for continuity)
            progress_callback: Progress callback
            section_index: Section index (for logging)
            
        Returns:
            Section content (Markdown format)
        """
        logger.info("Generating report section %s", section_index)
        
        # Record section start log
        if self.report_logger:
            self.report_logger.log_section_start(section.title, section_index)
        
        system_prompt = SECTION_SYSTEM_PROMPT_TEMPLATE.format(
            report_title=outline.title,
            report_summary=outline.summary,
            simulation_requirement=self.simulation_requirement,
            section_title=section.title,
            tools_description=self._get_tools_description(),
        )

        # Build user prompt - each completed chapter passes a maximum of 4000 characters
        if previous_sections:
            previous_parts = []
            for sec in previous_sections:
                # Max 4000 characters per section
                truncated = sec[:4000] + "..." if len(sec) > 4000 else sec
                previous_parts.append(truncated)
            previous_content = "\n\n---\n\n".join(previous_parts)
        else:
            previous_content = "(This is the first section)"
        
        user_prompt = SECTION_USER_PROMPT_TEMPLATE.format(
            previous_content=previous_content,
            section_title=section.title,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # ReACT loop
        tool_calls_count = 0
        max_iterations = 5  # Max iteration rounds
        min_tool_calls = 3  # Min tool calls required
        conflict_retries = 0  # Sequential conflicts between tool call and Final Answer
        used_tools = set()  # Record called tool names
        all_tools = {
            "insight_forge",
            "panorama_search",
            "quick_search",
            "simulation_observations",
            "interview_agents",
        }

        # Report context for InsightForge sub-query generation
        report_context = f"Section Title: {section.title}\nSimulation requirement: {self.simulation_requirement}"
        
        for iteration in range(max_iterations):
            if progress_callback:
                progress_callback(
                    "generating", 
                    int((iteration / max_iterations) * 100),
                    f"Retrieving and writing ({tool_calls_count}/{self.MAX_TOOL_CALLS_PER_SECTION})"
                )
            
            # Call LLM
            response = self.llm.chat(
                messages=messages,
                temperature=0.5,
                max_tokens=4096
            )
            self._generation_checkpoint()

            # Check if LLM response is None (API exception or empty content)
            if response is None:
                logger.warning(f"Section {section.title} iteration {iteration + 1}: LLM returned None")
                # If iterations left, add message and retry
                if iteration < max_iterations - 1:
                    messages.append({"role": "assistant", "content": "(empty response)"})
                    messages.append({"role": "user", "content": "Please continue generating content."})
                    continue
                # Last iteration also returns None, break loop and enter forced closure
                break

            logger.debug(f"LLM response: {response[:200]}...")

            # Parse once, reuse result
            tool_calls = self._parse_tool_calls(response)
            has_tool_calls = bool(tool_calls)
            has_final_answer = "Final Answer:" in response

            # -- Conflict handling: LLM output both tool call and Final Answer --
            if has_tool_calls and has_final_answer:
                conflict_retries += 1
                logger.warning(
                    f"Section {section.title} round {iteration+1}: "
                    f"LLM output both tool call and Final Answer (Conflict #{conflict_retries})"
                )

                if conflict_retries <= 2:
                    # First two times: Discard current response, request LLM to reply again
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": (
                            "[Format Error] You included both a tool call and Final Answer in one response, which is not allowed.\n"
                            "Each response must only do one of the following:\n"
                            "- Call a tool (output a <tool_call> block, don't write Final Answer)\n"
                            "- Output final content (start with 'Final Answer:', don't include <tool_call>)\n"
                            "Please reply again, doing only one of these."
                        ),
                    })
                    continue
                else:
                    # Third time: degrade, truncate to first tool call and execute
                    logger.warning(
                        f"Section {section.title}: {conflict_retries} sequential conflicts, "
                        "degrading to truncated execution of the first tool call"
                    )
                    first_tool_end = response.find('</tool_call>')
                    if first_tool_end != -1:
                        response = response[:first_tool_end + len('</tool_call>')]
                        tool_calls = self._parse_tool_calls(response)
                        has_tool_calls = bool(tool_calls)
                    has_final_answer = False
                    conflict_retries = 0

            # Record LLM response log
            if self.report_logger:
                self.report_logger.log_llm_response(
                    section_title=section.title,
                    section_index=section_index,
                    response=response,
                    iteration=iteration + 1,
                    has_tool_calls=has_tool_calls,
                    has_final_answer=has_final_answer
                )

            # -- Case 1: LLM output Final Answer --
            if has_final_answer:
                # Insufficient tool calls, reject and require more tools
                if tool_calls_count < min_tool_calls:
                    messages.append({"role": "assistant", "content": response})
                    unused_tools = all_tools - used_tools
                    unused_hint = f"(These tools are unused, recommended to use them: {', '.join(unused_tools)})" if unused_tools else ""
                    messages.append({
                        "role": "user",
                        "content": REACT_INSUFFICIENT_TOOLS_MSG.format(
                            tool_calls_count=tool_calls_count,
                            min_tool_calls=min_tool_calls,
                            unused_hint=unused_hint,
                        ),
                    })
                    continue

                # Normal finish
                final_answer = response.split("Final Answer:")[-1].strip()
                logger.info(
                    "Report section %s generation complete (tool_calls=%s)",
                    section_index,
                    tool_calls_count,
                )

                if self.report_logger:
                    self.report_logger.log_section_content(
                        section_title=section.title,
                        section_index=section_index,
                        content=final_answer,
                        tool_calls_count=tool_calls_count
                    )
                return final_answer

            # -- Case 2: LLM tries to call tool --
            if has_tool_calls:
                # Tool quota exhausted -> notify clearly, require Final Answer
                if tool_calls_count >= self.MAX_TOOL_CALLS_PER_SECTION:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": REACT_TOOL_LIMIT_MSG.format(
                            tool_calls_count=tool_calls_count,
                            max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        ),
                    })
                    continue

                # Execute only the first tool call
                call = tool_calls[0]
                if len(tool_calls) > 1:
                    logger.info(f"LLM tried to call {len(tool_calls)} tools, executing only the first: {call['name']}")

                if self.report_logger:
                    self.report_logger.log_tool_call(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        parameters=call.get("parameters", {}),
                        iteration=iteration + 1
                    )

                result = self._execute_tool(
                    call["name"],
                    call.get("parameters", {}),
                    report_context=report_context
                )
                self._generation_checkpoint()

                if self.report_logger:
                    self.report_logger.log_tool_result(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        result=result,
                        iteration=iteration + 1
                    )

                tool_calls_count += 1
                used_tools.add(call['name'])

                # Build unused tools hint
                unused_tools = all_tools - used_tools
                unused_hint = ""
                if unused_tools and tool_calls_count < self.MAX_TOOL_CALLS_PER_SECTION:
                    unused_hint = REACT_UNUSED_TOOLS_HINT.format(unused_list=", ".join(unused_tools))

                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": REACT_OBSERVATION_TEMPLATE.format(
                        tool_name=call["name"],
                        result=result,
                        tool_calls_count=tool_calls_count,
                        max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        used_tools_str=", ".join(used_tools),
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # -- Case 3: Neither tool call nor Final Answer --
            messages.append({"role": "assistant", "content": response})

            if tool_calls_count < min_tool_calls:
                # Insufficient tool calls, recommend unused tools
                unused_tools = all_tools - used_tools
                unused_hint = f"(These tools are unused, recommended to use them: {', '.join(unused_tools)})" if unused_tools else ""
                
                messages.append({
                    "role": "user",
                    "content": REACT_INSUFFICIENT_TOOLS_MSG_ALT.format(
                        tool_calls_count=tool_calls_count,
                        min_tool_calls=min_tool_calls,
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # Sufficient tool calls, LLM output content but without "Final Answer:" prefix
            # Directly adopt this content as final answer, stop spinning
            logger.info(
                "Report section %s completed without the expected final-answer "
                "prefix (tool_calls=%s)",
                section_index,
                tool_calls_count,
            )
            final_answer = response.strip()

            if self.report_logger:
                self.report_logger.log_section_content(
                    section_title=section.title,
                    section_index=section_index,
                    content=final_answer,
                    tool_calls_count=tool_calls_count
                )
            return final_answer
        
        # Max iterations reached, force content generation
        logger.warning(f"Section {section.title} reached max iterations; forcing generation")
        messages.append({"role": "user", "content": REACT_FORCE_FINAL_MSG})
        
        response = self.llm.chat(
            messages=messages,
            temperature=0.5,
            max_tokens=4096
        )
        self._generation_checkpoint()

        # Check if LLM returned None during forced closure
        if response is None:
            logger.error(f"Section {section.title} forced closure LLM returned None, using default error message")
            final_answer = "(This section failed to generate: LLM returned empty response, please try again later)"
        elif "Final Answer:" in response:
            final_answer = response.split("Final Answer:")[-1].strip()
        else:
            final_answer = response
        
        # Record section content generation complete log
        if self.report_logger:
            self.report_logger.log_section_content(
                section_title=section.title,
                section_index=section_index,
                content=final_answer,
                tool_calls_count=tool_calls_count
            )
        
        return final_answer
    
    def generate_report(
        self, 
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        report_id: Optional[str] = None,
        generation_lease: ReportGenerationLease | None = None,
    ) -> Report:
        """
        Generate full report (chapter by chapter real-time output)
        
        Saves each chapter immediately to the folder upon completion, no need to wait for the whole report.
        File structure:
        reports/{report_id}/
            meta.json       - Report meta info
            outline.json    - Report outline property info
            progress.json   - Generation progress
            section_01.md   - Section 1
            section_02.md   - Section 2
            ...
            full_report.md  - Full report
        
        Args:
            progress_callback: Progress callback (stage, progress, message)
            report_id: Report ID (optional, auto-generated if not provided)
            
        Returns:
            Report: Full report
        """
        import uuid
        
        # If no report_id provided, generate automatically
        if not report_id:
            report_id = f"report_{uuid.uuid4().hex[:12]}"
        self._generation_lease = generation_lease
        self._generation_checkpoint()
        start_time = datetime.now()
        
        report = Report(
            report_id=report_id,
            simulation_id=self.simulation_id,
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement,
            status=ReportStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        
        # Completed section titles list (for progress tracking)
        completed_section_titles = []
        
        try:
            # Initialization: Create report folder and save initial state
            with self._generation_write_guard():
                ReportManager._ensure_report_folder(report_id)
            
            # Initialize logger (structured log agent_log.jsonl)
            with self._generation_write_guard():
                self.report_logger = ReportLogger(
                    report_id,
                    generation_lease=generation_lease,
                )
            self.report_logger.log_start(
                simulation_id=self.simulation_id,
                graph_id=self.graph_id,
                simulation_requirement=self.simulation_requirement
            )
            
            # Detailed production traces remain structured and privacy-safe.
            # The duplicate plain-text console file is local-debug-only.
            if Config.DEBUG and generation_lease is None:
                self.console_logger = ReportConsoleLogger(report_id)
            
            with self._generation_write_guard():
                ReportManager.update_progress(
                    report_id, "pending", 0, "Initializing report...",
                    completed_sections=[]
                )
                ReportManager.save_report(report)
            
            # Phase 1: Plan outline
            report.status = ReportStatus.PLANNING
            with self._generation_write_guard():
                ReportManager.update_progress(
                    report_id, "planning", 5, "Starting report outline planning...",
                    completed_sections=[]
                )
            
            # Log planning start
            self.report_logger.log_planning_start()
            
            if progress_callback:
                progress_callback("planning", 0, "Starting report outline planning...")
            
            outline = self.plan_outline(
                progress_callback=lambda stage, prog, msg: 
                    progress_callback(stage, prog // 5, msg) if progress_callback else None
            )
            self._generation_checkpoint()
            report.outline = outline
            
            # Log Planning complete
            self.report_logger.log_planning_complete(outline.to_dict())
            
            # Save outline to file
            with self._generation_write_guard():
                ReportManager.save_outline(report_id, outline)
                ReportManager.update_progress(
                    report_id, "planning", 15, f"Outline planning complete, {len(outline.sections)} sections",
                    completed_sections=[]
                )
                ReportManager.save_report(report)
            
            logger.info(f"Outline saved to file: {report_id}/outline.json")
            
            # Phase 2: Generate chapter by chapter (save by chapter)
            report.status = ReportStatus.GENERATING
            
            total_sections = len(outline.sections)
            generated_sections = []  # Save content for context
            
            for i, section in enumerate(outline.sections):
                self._generation_checkpoint()
                section_num = i + 1
                base_progress = 20 + int((i / total_sections) * 70)
                
                # Update progress
                with self._generation_write_guard():
                    ReportManager.update_progress(
                        report_id, "generating", base_progress,
                        f"Generating section: {section.title} ({section_num}/{total_sections})",
                        current_section=section.title,
                        completed_sections=completed_section_titles
                    )
                
                if progress_callback:
                    progress_callback(
                        "generating", 
                        base_progress, 
                        f"Generating section: {section.title} ({section_num}/{total_sections})"
                    )
                
                # Generate main section content
                section_content = self._generate_section_react(
                    section=section,
                    outline=outline,
                    previous_sections=generated_sections,
                    progress_callback=lambda stage, prog, msg:
                        progress_callback(
                            stage, 
                            base_progress + int(prog * 0.7 / total_sections),
                            msg
                        ) if progress_callback else None,
                    section_index=section_num
                )
                self._generation_checkpoint()
                
                section.content = section_content
                generated_sections.append(f"## {section.title}\n\n{section_content}")

                # Save section
                with self._generation_write_guard():
                    ReportManager.save_section(report_id, section_num, section)
                completed_section_titles.append(section.title)

                # Log section complete
                full_section_content = f"## {section.title}\n\n{section_content}"

                if self.report_logger:
                    self.report_logger.log_section_full_complete(
                        section_title=section.title,
                        section_index=section_num,
                        full_content=full_section_content.strip()
                    )

                logger.info(f"Section saved: {report_id}/section_{section_num:02d}.md")
                
                # Update progress
                with self._generation_write_guard():
                    ReportManager.update_progress(
                        report_id, "generating",
                        base_progress + int(70 / total_sections),
                        f"Section {section.title} completed",
                        current_section=None,
                        completed_sections=completed_section_titles
                    )
            
            # Phase 3: Assemble Full report
            self._generation_checkpoint()
            if progress_callback:
                progress_callback("generating", 95, "Assembling Full report...")
            
            with self._generation_write_guard():
                ReportManager.update_progress(
                    report_id, "generating", 95, "Assembling Full report...",
                    completed_sections=completed_section_titles
                )
            
            # Use ReportManager to assemble Full report
            with self._generation_write_guard():
                report.markdown_content = ReportManager.assemble_full_report(
                    report_id,
                    outline,
                )
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now().isoformat()

            simulation_dir = os.path.join(Config.UPLOAD_FOLDER, "simulations", self.simulation_id)
            report_dir = ReportManager._get_report_folder(report_id)
            if os.path.isdir(simulation_dir):
                with self._generation_write_guard():
                    build_report_evidence(
                        report_id=report_id,
                        report_dir=report_dir,
                        simulation_dir=simulation_dir,
                        outline=outline,
                    )
            else:
                logger.warning(f"Skipping report evidence generation, simulation directory does not exist: {simulation_dir}")
            
            # Calculate total time taken
            total_time_seconds = (datetime.now() - start_time).total_seconds()
            
            # Log report complete
            if self.report_logger:
                self.report_logger.log_report_complete(
                    total_sections=total_sections,
                    total_time_seconds=total_time_seconds
                )
            
            # Save final report
            with self._generation_write_guard():
                ReportManager.save_report(report)
                ReportManager.update_progress(
                    report_id, "completed", 100, "Report generation complete",
                    completed_sections=completed_section_titles
                )
            
            if progress_callback:
                progress_callback("completed", 100, "Report generation complete")
            
            logger.info(f"Report generation complete: {report_id}")
            
            # Close console logger
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
            
        except ReportGenerationCancelled:
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            raise
        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")
            report.status = ReportStatus.FAILED
            report.error = str(e) if Config.DEBUG else "Report generation failed"
            
            # Record error log
            if self.report_logger:
                self.report_logger.log_error(str(e), "failed")
            
            # Save failed status
            try:
                with self._generation_write_guard():
                    ReportManager.save_report(report)
                    ReportManager.update_progress(
                        report_id,
                        "failed",
                        -1,
                        (
                            f"Report generation failed: {str(e)}"
                            if Config.DEBUG
                            else "Report generation failed"
                        ),
                        completed_sections=completed_section_titles
                    )
            except Exception:
                pass  # Ignore errors during saving failure status
            
            # Close console logger
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
    
    def chat(
        self, 
        message: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Chat with Report Agent
        
        The Agent can autonomously call retrieval tools to answer questions during the conversation.
        
        Args:
            message: User message
            chat_history: Chat history
            
        Returns:
            {
                "response": "Agent response",
                "tool_calls": [list of called tools],
                "retrieval_queries": [graph or run-record search queries]
            }
        """
        logger.info("Report Agent chat request received (characters=%s)", len(message))
        
        chat_history = chat_history or []
        
        # Get generated report content
        report_content = ""
        try:
            report = ReportManager.get_report_by_simulation(self.simulation_id)
            if report and report.markdown_content:
                # Limit report length to avoid excessive context
                report_content = report.markdown_content[:15000]
                if len(report.markdown_content) > 15000:
                    report_content += "\n\n... [Report content truncated] ..."
        except Exception as e:
            logger.warning(
                "Failed to get report content (%s)",
                type(e).__name__,
            )
        
        system_prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            report_content=report_content if report_content else "(No report yet)",
            tools_description=self._get_tools_description(),
        )

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add historical conversations
        for h in chat_history[-10:]:  # Limit history length
            messages.append(h)
        
        # Add user message
        messages.append({
            "role": "user", 
            "content": message
        })
        
        # ReACT loop (simplified)
        tool_calls_made = []
        max_iterations = 2  # Reduce number of iterations
        
        for iteration in range(max_iterations):
            response = self.llm.chat(
                messages=messages,
                temperature=0.5
            )
            
            # Parse tool calls
            tool_calls = self._parse_tool_calls(response)
            
            if not tool_calls:
                # No tool calls, return response directly
                clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', response, flags=re.DOTALL)
                clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
                
                retrieval_queries = [
                    tc.get("parameters", {}).get("query", "")
                    for tc in tool_calls_made
                ]
                return {
                    "response": clean_response.strip(),
                    "tool_calls": tool_calls_made,
                    "retrieval_queries": retrieval_queries,
                }
            
            # Execute tool calls (limited quantity)
            tool_results = []
            for call in tool_calls[:1]:  # Execute at most 1 tool call per round
                if len(tool_calls_made) >= self.MAX_TOOL_CALLS_PER_CHAT:
                    break
                result = self._execute_tool(call["name"], call.get("parameters", {}))
                tool_results.append({
                    "tool": call["name"],
                    "result": result[:1500]  # Limit result length
                })
                tool_calls_made.append(call)
            
            # Add results to messages
            messages.append({"role": "assistant", "content": response})
            observation = "\n".join([f"[{r['tool']} result]\n{r['result']}" for r in tool_results])
            messages.append({
                "role": "user",
                "content": observation + CHAT_OBSERVATION_SUFFIX
            })
        
        # Reached max iterations, get final response
        final_response = self.llm.chat(
            messages=messages,
            temperature=0.5
        )
        
        # Clean response
        clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', final_response, flags=re.DOTALL)
        clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
        
        retrieval_queries = [
            tc.get("parameters", {}).get("query", "")
            for tc in tool_calls_made
        ]
        return {
            "response": clean_response.strip(),
            "tool_calls": tool_calls_made,
            "retrieval_queries": retrieval_queries,
        }


class ReportManager:
    """
    Report Manager
    
    Responsible for persistent storage and retrieval of reports.
    
    File structure (chapter by chapter output):
    reports/
      {report_id}/
        meta.json          - Report meta information and status
        outline.json       - Report outline
        progress.json      - Generation progress
        section_01.md      - Section 1
        section_02.md      - Section 2
        ...
        full_report.md     - Full report
    """
    
    # Report storage directory
    REPORTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'reports')
    
    @classmethod
    def _ensure_reports_dir(cls):
        """Ensure report root directory exists"""
        os.makedirs(cls.REPORTS_DIR, exist_ok=True)
    
    @classmethod
    def _get_report_folder(cls, report_id: str) -> str:
        """Get report folder path"""
        from ..utils.safe_path import safe_join
        return safe_join(cls.REPORTS_DIR, report_id)
    
    @classmethod
    def _ensure_report_folder(cls, report_id: str) -> str:
        """Ensure report folder exists and return path"""
        folder = cls._get_report_folder(report_id)
        os.makedirs(folder, exist_ok=True)
        return folder
    
    @classmethod
    def _get_report_path(cls, report_id: str) -> str:
        """Get report meta information file path"""
        return os.path.join(cls._get_report_folder(report_id), "meta.json")
    
    @classmethod
    def _get_report_markdown_path(cls, report_id: str) -> str:
        """Get Full report Markdown file path"""
        return os.path.join(cls._get_report_folder(report_id), "full_report.md")
    
    @classmethod
    def _get_outline_path(cls, report_id: str) -> str:
        """Get outline file path"""
        return os.path.join(cls._get_report_folder(report_id), "outline.json")
    
    @classmethod
    def _get_progress_path(cls, report_id: str) -> str:
        """Get progress file path"""
        return os.path.join(cls._get_report_folder(report_id), "progress.json")
    
    @classmethod
    def _get_section_path(cls, report_id: str, section_index: int) -> str:
        """Get chapter Markdown file path"""
        return os.path.join(cls._get_report_folder(report_id), f"section_{section_index:02d}.md")
    
    @classmethod
    def _get_agent_log_path(cls, report_id: str) -> str:
        """Get Agent log file path"""
        return os.path.join(cls._get_report_folder(report_id), "agent_log.jsonl")
    
    @classmethod
    def _get_console_log_path(cls, report_id: str) -> str:
        """Get console log file path"""
        return os.path.join(cls._get_report_folder(report_id), "console_log.txt")
    
    @classmethod
    def get_console_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        Get console log content
        
        This is the console output log (INFO, WARNING, etc.) during report generation,
        different from the structured log in agent_log.jsonl.
        
        Args:
            report_id: Report ID
            from_line: Start reading from which line (for incremental fetching, 0 means from the beginning)
            
        Returns:
            {
                "logs": [list of log lines],
                "total_lines": total number of lines,
                "from_line": starting line number,
                "has_more": whether there are more logs
            }
        """
        log_path = cls._get_console_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    # Keep original log line, remove trailing newline
                    logs.append(line.rstrip('\n\r'))
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # Already read to the end
        }
    
    @classmethod
    def get_console_log_stream(cls, report_id: str) -> List[str]:
        """
        Get full console log (fetch all at once)
        
        Args:
            report_id: Report ID
            
        Returns:
            List of log lines
        """
        result = cls.get_console_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def get_agent_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        Get Agent log content
        
        Args:
            report_id: Report ID
            from_line: Start reading from which line (for incremental fetching, 0 means from the beginning)
            
        Returns:
            {
                "logs": [list of log entries],
                "total_lines": total number of lines,
                "from_line": starting line number,
                "has_more": whether there are more logs
            }
        """
        log_path = cls._get_agent_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        # Skip failed parsing lines
                        continue
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # Already read to the end
        }
    
    @classmethod
    def get_agent_log_stream(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        Get full Agent log (fetch all at once)
        
        Args:
            report_id: Report ID
            
        Returns:
            List of log entries
        """
        result = cls.get_agent_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def save_outline(cls, report_id: str, outline: ReportOutline) -> None:
        """
        Save Report outline
        
        Called immediately after the planning phase is complete.
        """
        cls._ensure_report_folder(report_id)
        
        with open(cls._get_outline_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(outline.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"Outline saved: {report_id}")
    
    @classmethod
    def save_section(
        cls,
        report_id: str,
        section_index: int,
        section: ReportSection
    ) -> str:
        """
        Save a single section

        Called immediately after each section is generated, enabling chapter-by-chapter output.

        Args:
            report_id: Report ID
            section_index: Section index (starts from 1)
            section: Section object

        Returns:
            Path to the saved file
        """
        cls._ensure_report_folder(report_id)

        # Build section Markdown content - clean up any duplicate titles
        cleaned_content = cls._clean_section_content(section.content, section.title)
        md_content = f"## {section.title}\n\n"
        if cleaned_content:
            md_content += f"{cleaned_content}\n\n"

        # Save file
        file_suffix = f"section_{section_index:02d}.md"
        file_path = os.path.join(cls._get_report_folder(report_id), file_suffix)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        logger.info(f"Section saved: {report_id}/{file_suffix}")
        return file_path
    
    @classmethod
    def _clean_section_content(cls, content: str, section_title: str) -> str:
        """
        Clean section content
        
        1. Remove Markdown heading lines at the beginning of the content that duplicate the section title.
        2. Convert all ### and lower-level headings to bold text.
        
        Args:
            content: Original content
            section_title: Section title
            
        Returns:
            Cleaned content
        """
        import re
        
        if not content:
            return content
        
        content = content.strip()
        lines = content.split('\n')
        cleaned_lines = []
        skip_next_empty = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Check if it's a Markdown heading line
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title_text = heading_match.group(2).strip()
                
                # Check if it's a duplicate heading of the section title (within the first 5 lines)
                if i < 5:
                    if title_text == section_title or title_text.replace(' ', '') == section_title.replace(' ', ''):
                        skip_next_empty = True
                        continue
                
                # Convert all levels of headings (#, ##, ###, ####, etc.) to bold
                # Because section titles are added by the system, there should be no headings within the content.
                cleaned_lines.append(f"**{title_text}**")
                cleaned_lines.append("")  # Add empty line
                continue
            
            # If the previous line was a skipped heading and the current line is empty, skip it too
            if skip_next_empty and stripped == '':
                skip_next_empty = False
                continue
            
            skip_next_empty = False
            cleaned_lines.append(line)
        
        # Remove leading empty lines
        while cleaned_lines and cleaned_lines[0].strip() == '':
            cleaned_lines.pop(0)
        
        # Remove leading separators
        while cleaned_lines and cleaned_lines[0].strip() in ['---', '***', '___']:
            cleaned_lines.pop(0)
            # Also remove empty lines after the separator
            while cleaned_lines and cleaned_lines[0].strip() == '':
                cleaned_lines.pop(0)
        
        return '\n'.join(cleaned_lines)
    
    @classmethod
    def update_progress(
        cls, 
        report_id: str, 
        status: str, 
        progress: int, 
        message: str,
        current_section: str = None,
        completed_sections: List[str] = None
    ) -> None:
        """
        Update report generation progress
        
        Frontend can get real-time progress by reading progress.json
        """
        cls._ensure_report_folder(report_id)
        
        progress_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "current_section": current_section,
            "completed_sections": completed_sections or [],
            "updated_at": datetime.now().isoformat()
        }
        
        with open(cls._get_progress_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def get_progress(cls, report_id: str) -> Optional[Dict[str, Any]]:
        """Get report generation progress"""
        path = cls._get_progress_path(report_id)
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @classmethod
    def get_generated_sections(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        Get list of generated sections
        
        Returns information for all saved section files.
        """
        folder = cls._get_report_folder(report_id)
        
        if not os.path.exists(folder):
            return []
        
        sections = []
        for filename in sorted(os.listdir(folder)):
            if filename.startswith('section_') and filename.endswith('.md'):
                file_path = os.path.join(folder, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse section index from filename
                parts = filename.replace('.md', '').split('_')
                section_index = int(parts[1])

                sections.append({
                    "filename": filename,
                    "section_index": section_index,
                    "content": content
                })

        return sections
    
    @classmethod
    def assemble_full_report(cls, report_id: str, outline: ReportOutline) -> str:
        """
        Assemble Full report
        
        Assembles the full report from saved section files and cleans up headings.
        """
        folder = cls._get_report_folder(report_id)
        
        # Build report header
        md_content = f"# {outline.title}\n\n"
        md_content += f"> {outline.summary}\n\n"
        md_content += f"> {SYNTHETIC_REPORT_DISCLOSURE}\n\n"
        md_content += f"---\n\n"
        
        # Read all section files in order
        sections = cls.get_generated_sections(report_id)
        for section_info in sections:
            md_content += section_info["content"]
        
        # Post-process: clean up heading issues for the entire report
        md_content = cls._post_process_report(md_content, outline)
        
        # Save Full report
        full_path = cls._get_report_markdown_path(report_id)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"Full report assembled: {report_id}")
        return md_content
    
    @classmethod
    def _post_process_report(cls, content: str, outline: ReportOutline) -> str:
        """
        Post-process report content
        
        1. Remove duplicate headings.
        2. Keep main report title (#) and section titles (##), remove other levels of headings (###, ####, etc.).
        3. Clean up extra empty lines and separators.
        
        Args:
            content: Original report content
            outline: Report outline
            
        Returns:
            Processed content
        """
        import re
        
        lines = content.split('\n')
        processed_lines = []
        prev_was_heading = False
        
        # Collect all section titles from the outline
        section_titles = set()
        for section in outline.sections:
            section_titles.add(section.title)
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Check if it's a heading line
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # Check for duplicate headings (same content heading within 5 consecutive lines)
                is_duplicate = False
                for j in range(max(0, len(processed_lines) - 5), len(processed_lines)):
                    prev_line = processed_lines[j].strip()
                    prev_match = re.match(r'^(#{1,6})\s+(.+)$', prev_line)
                    if prev_match:
                        prev_title = prev_match.group(2).strip()
                        if prev_title == title:
                            is_duplicate = True
                            break
                
                if is_duplicate:
                    # Skip duplicate heading and subsequent empty lines
                    i += 1
                    while i < len(lines) and lines[i].strip() == '':
                        i += 1
                    continue
                
                # Heading level processing:
                # - # (level=1) Only keep the main report title
                # - ## (level=2) Keep section titles
                # - ### and below (level>=3) Convert to bold text
                
                if level == 1:
                    if title == outline.title:
                        # Keep main report title
                        processed_lines.append(line)
                        prev_was_heading = True
                    elif title in section_titles:
                        # Section title incorrectly used #, correct to ##
                        processed_lines.append(f"## {title}")
                        prev_was_heading = True
                    else:
                        # Other level 1 headings convert to bold
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                elif level == 2:
                    if title in section_titles or title == outline.title:
                        # Keep section title
                        processed_lines.append(line)
                        prev_was_heading = True
                    else:
                        # Non-section level 2 headings convert to bold
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                else:
                    # ### and lower-level headings convert to bold text
                    processed_lines.append(f"**{title}**")
                    processed_lines.append("")
                    prev_was_heading = False
                
                i += 1
                continue
            
            elif stripped == '---' and prev_was_heading:
                # Skip separator immediately following a heading
                i += 1
                continue
            
            elif stripped == '' and prev_was_heading:
                # Only keep one empty line after a heading
                if processed_lines and processed_lines[-1].strip() != '':
                    processed_lines.append(line)
                prev_was_heading = False
            
            else:
                processed_lines.append(line)
                prev_was_heading = False
            
            i += 1
        
        # Clean up multiple consecutive empty lines (keep at most 2)
        result_lines = []
        empty_count = 0
        for line in processed_lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:
                    result_lines.append(line)
            else:
                empty_count = 0
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    @classmethod
    def save_report(cls, report: Report) -> None:
        """Save report meta information and Full report"""
        cls._ensure_report_folder(report.report_id)
        
        # Save meta information JSON
        with open(cls._get_report_path(report.report_id), 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        
        # Save outline
        if report.outline:
            cls.save_outline(report.report_id, report.outline)
        
        # Save full Markdown report
        if report.markdown_content:
            with open(cls._get_report_markdown_path(report.report_id), 'w', encoding='utf-8') as f:
                f.write(report.markdown_content)
        
        logger.info(f"Report saved: {report.report_id}")
    
    @classmethod
    def get_report(cls, report_id: str) -> Optional[Report]:
        """Get report"""
        path = cls._get_report_path(report_id)

        if not os.path.exists(path):
            # Compatibility with old format: check directly in reports directory
            # (path-traversal defense: route report_id through safe_join).
            from ..utils.safe_path import safe_join
            old_path = safe_join(cls.REPORTS_DIR, report_id + ".json")
            if os.path.exists(old_path):
                path = old_path
            else:
                return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reconstruct Report object
        outline = None
        if data.get('outline'):
            outline_data = data['outline']
            sections = []
            for s in outline_data.get('sections', []):
                sections.append(ReportSection(
                    title=s['title'],
                    content=s.get('content', '')
                ))
            outline = ReportOutline(
                title=outline_data['title'],
                summary=outline_data['summary'],
                sections=sections
            )
        
        # If markdown_content is empty, try reading from full_report.md
        markdown_content = data.get('markdown_content', '')
        if not markdown_content:
            full_report_path = cls._get_report_markdown_path(report_id)
            if os.path.exists(full_report_path):
                with open(full_report_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
        
        return Report(
            report_id=data['report_id'],
            simulation_id=data['simulation_id'],
            graph_id=data['graph_id'],
            simulation_requirement=data['simulation_requirement'],
            status=ReportStatus(data['status']),
            outline=outline,
            markdown_content=markdown_content,
            created_at=data.get('created_at', ''),
            completed_at=data.get('completed_at', ''),
            error=data.get('error')
        )
    
    @classmethod
    def get_report_by_simulation(cls, simulation_id: str) -> Optional[Report]:
        """Get report by simulation ID"""
        cls._ensure_reports_dir()
        
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # New format: folder
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report and report.simulation_id == simulation_id:
                    return report
            # Compatible with old format: JSON file
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report and report.simulation_id == simulation_id:
                    return report
        
        return None
    
    @classmethod
    def list_reports(cls, simulation_id: Optional[str] = None, limit: int = 50) -> List[Report]:
        """List reports"""
        cls._ensure_reports_dir()
        
        reports = []
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
            # Compatibility with old format: JSON file
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
        
        # Sort by creation time descending
        reports.sort(key=lambda r: r.created_at, reverse=True)
        
        return reports[:limit]
    
    @classmethod
    def delete_report(cls, report_id: str) -> bool:
        """Delete report (entire folder)"""
        import shutil
        
        folder_path = cls._get_report_folder(report_id)
        
        # New format: delete entire folder
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            logger.info(f"Report folder deleted: {report_id}")
            return True
        
        # Compatibility with old format: delete individual files
        # (path-traversal defense: route report_id through safe_join — note
        # _get_report_folder above already validates, but keep this layer too).
        from ..utils.safe_path import safe_join
        deleted = False
        old_json_path = safe_join(cls.REPORTS_DIR, report_id + ".json")
        old_md_path = safe_join(cls.REPORTS_DIR, report_id + ".md")
        
        if os.path.exists(old_json_path):
            os.remove(old_json_path)
            deleted = True
        if os.path.exists(old_md_path):
            os.remove(old_md_path)
            deleted = True
        
        return deleted
