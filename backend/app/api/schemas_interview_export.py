"""Typed request bodies for the interview and generated-response export routes.

Exec-plan T26, slice 3. Shape only: JSON types and unknown keys. Every bound
these routes actually enforce -- prompt length, batch size, timeout range --
already lives in ``utils.input_policy`` and answers with a specific code that
existing tests assert on and clients branch on. Repeating those limits here
would replace several working codes with one generic one, so they are left
where they are.

``strict=True`` is the opposite trade, and it is the reason this module exists.
Without it Pydantic coerces ``"raw": "yes"`` to True and ``simulation_id: 5``
to ``"5"``. The first grants a prompt-optimisation bypass the client never sent
as a flag, the second invents an identifier, and neither route checks types
itself, so both coercions would be silent.

Every field is optional on purpose. The handlers own the "missing X" responses
and their codes; making a field required here would collapse two distinct 400s
into one and break clients that branch on them.

``extra="forbid"`` is used on every model here, and that is evidence-backed
rather than defaulted. For each body route in these two modules, every key the
client can legitimately send is a key the handler already reads:

* the single, batch and all-profiles routes read ``simulation_id``,
  ``agent_id``, ``prompt``, ``platform``, ``timeout``, and the DEBUG-gated
  ``raw`` / ``bypass_prompt_optimization``;
* the history route reads ``simulation_id``, ``platform``, ``agent_id`` and
  ``limit``;
* the export route reads ``results``, and ``CSVExporter.export_survey_results``
  consumes each item's ``agent_name``, ``profession`` and ``answer``.

No backend test and no caller under ``frontend/src`` posts a key outside those
sets (``tests/test_input_policy.py``, ``tests/test_api_claim_boundary.py``,
``tests/test_export_service.py``, ``Step5Interaction.vue``). Contrast
``GenerateReportRequest``, which must use ``extra="ignore"`` because a
provenance test posts client-supplied canaries the handler has to reach in
order to discard; refusing them there would make that guarantee untestable.

``platform`` stays a plain string rather than an enum. The handlers already
reject an unsupported value with their own wording, and constraining it here
would move that answer onto a different code.

The two download routes in ``export_routes`` take only a path parameter, read
no request body, and therefore get no model.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class InterviewQuestion(BaseModel):
    """One follow-up question item.

    ``platform`` is per-item and may override the request-level default; the
    handlers keep that precedence, so this model only types it.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    agent_id: Optional[int] = None
    prompt: Optional[str] = None
    platform: Optional[str] = None
    # Read by the handlers only under Config.DEBUG, but still declared: a
    # DEBUG-gated key is still a legitimate key, and forbidding it would reject
    # a documented payload.
    raw: Optional[bool] = None
    bypass_prompt_optimization: Optional[bool] = None


class InterviewAgentRequest(BaseModel):
    """Single follow-up question body.

    No max_length on ``prompt`` and no range on ``timeout``: both belong to
    ``bounded_text`` / ``bounded_integer``, which answer ``text_field_too_long``
    and ``integer_field_out_of_range``.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    simulation_id: Optional[str] = None
    agent_id: Optional[int] = None
    prompt: Optional[str] = None
    platform: Optional[str] = None
    timeout: Optional[int] = None
    raw: Optional[bool] = None
    bypass_prompt_optimization: Optional[bool] = None


class InterviewAgentsBatchRequest(BaseModel):
    """Batch follow-up body.

    No cap on ``questions``: ``validate_item_count`` answers ``too_many_items``
    against ``INTERVIEW_BATCH_MAX`` and that code is asserted by
    ``tests/test_input_policy.py``.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    simulation_id: Optional[str] = None
    questions: Optional[List[InterviewQuestion]] = None
    # Legacy alias. The handler reads ``questions or interviews``, so it is a
    # supported key of this route and not an unknown one.
    interviews: Optional[List[InterviewQuestion]] = None
    platform: Optional[str] = None
    timeout: Optional[int] = None
    raw: Optional[bool] = None
    bypass_prompt_optimization: Optional[bool] = None


class InterviewAllAgentsRequest(BaseModel):
    """One question asked of every generated profile."""

    model_config = ConfigDict(extra="forbid", strict=True)

    simulation_id: Optional[str] = None
    prompt: Optional[str] = None
    platform: Optional[str] = None
    timeout: Optional[int] = None
    raw: Optional[bool] = None
    bypass_prompt_optimization: Optional[bool] = None


class InterviewHistoryRequest(BaseModel):
    """Saved follow-up record lookup.

    This handler performs no ``input_policy`` validation at all, so the bounds
    question does not arise here; ``limit`` is typed only.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    simulation_id: Optional[str] = None
    platform: Optional[str] = None
    agent_id: Optional[int] = None
    limit: Optional[int] = None


class ExportedGeneratedResponse(BaseModel):
    """One client-supplied record in a generated-response export.

    ``extra="forbid"`` matters more here than elsewhere: the exporter spreads
    every key of the item into the CSV, so an unrecognised key would silently
    become an extra column. The three documented keys are all the frontend ever
    sends.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    agent_name: Optional[str] = None
    profession: Optional[str] = None
    answer: Optional[str] = None


class ExportGeneratedResponsesRequest(BaseModel):
    """Export body.

    ``results`` stays optional and uncapped: emptiness is the handler's call
    (``No results to export``) and there is no length policy on this route to
    duplicate.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    results: Optional[List[ExportedGeneratedResponse]] = None