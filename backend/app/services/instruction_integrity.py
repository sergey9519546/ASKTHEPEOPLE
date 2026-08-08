"""Immutable system-instruction and tool-set checks for runtime agents."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


def _sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class InstructionIntegrityRecordV1:
    agent_id: int
    role_name: str
    tool_names: tuple[str, ...]
    tool_contracts_sha256: str
    system_message_sha256: str
    canonical_sha256: str


class InstructionIntegrityViolation(RuntimeError):
    """Hash-only failure safe for operational logs."""

    def __init__(
        self,
        *,
        agent_id: int | None,
        expected_sha256: str,
        actual_sha256: str,
    ) -> None:
        self.code = "instruction_integrity_violation"
        self.agent_id = agent_id
        self.expected_sha256 = expected_sha256
        self.actual_sha256 = actual_sha256
        super().__init__(
            f"{self.code}: agent_id={agent_id}; "
            f"expected_sha256={expected_sha256}; "
            f"actual_sha256={actual_sha256}"
        )


class InstructionIntegrityGuard:
    """Capture once, then verify exact prompt/role/tool identities."""

    def __init__(self, records: tuple[InstructionIntegrityRecordV1, ...]):
        self._records = records

    @classmethod
    def capture(cls, agents: Any) -> InstructionIntegrityGuard:
        return cls(_snapshot(agents))

    def verify(self, agents: Any) -> None:
        actual = _snapshot(agents)
        expected_by_id = {record.agent_id: record for record in self._records}
        actual_by_id = {record.agent_id: record for record in actual}
        if set(expected_by_id) != set(actual_by_id):
            changed_ids = sorted(set(expected_by_id) ^ set(actual_by_id))
            agent_id = changed_ids[0] if changed_ids else None
            raise InstructionIntegrityViolation(
                agent_id=agent_id,
                expected_sha256=_record_set_sha256(self._records),
                actual_sha256=_record_set_sha256(actual),
            )
        for agent_id in sorted(expected_by_id):
            expected = expected_by_id[agent_id]
            current = actual_by_id[agent_id]
            if expected.canonical_sha256 != current.canonical_sha256:
                raise InstructionIntegrityViolation(
                    agent_id=agent_id,
                    expected_sha256=expected.canonical_sha256,
                    actual_sha256=current.canonical_sha256,
                )

    def manifest(self) -> dict[str, object]:
        return {
            "schema_version": "instruction-integrity/v1",
            "agents": [
                {
                    "agent_id": record.agent_id,
                    "system_message_sha256": record.system_message_sha256,
                    "canonical_sha256": record.canonical_sha256,
                    "tool_contracts_sha256": record.tool_contracts_sha256,
                }
                for record in self._records
            ],
            "record_set_sha256": _record_set_sha256(self._records),
        }


def _snapshot(agents: Any) -> tuple[InstructionIntegrityRecordV1, ...]:
    records = tuple(
        sorted(
            (_record(agent) for agent in _agents(agents)),
            key=lambda item: item.agent_id,
        )
    )
    if len({record.agent_id for record in records}) != len(records):
        raise InstructionIntegrityViolation(
            agent_id=None,
            expected_sha256="",
            actual_sha256=_record_set_sha256(records),
        )
    return records


def _agents(source: Any) -> Iterable[Any]:
    if hasattr(source, "get_agents"):
        values = source.get_agents()
    else:
        values = source
    for value in values:
        if (
            isinstance(value, tuple)
            and len(value) == 2
            and isinstance(value[0], int)
        ):
            yield value[1]
        else:
            yield value


def _record(agent: Any) -> InstructionIntegrityRecordV1:
    agent_id = getattr(agent, "social_agent_id", None)
    message = getattr(agent, "system_message", None)
    role_name = getattr(message, "role_name", None)
    content = getattr(message, "content", None)
    if (
        not isinstance(agent_id, int)
        or not isinstance(role_name, str)
        or not isinstance(content, str)
    ):
        raise InstructionIntegrityViolation(
            agent_id=agent_id if isinstance(agent_id, int) else None,
            expected_sha256="",
            actual_sha256="",
        )
    tools = getattr(agent, "tool_dict", {})
    if not isinstance(tools, Mapping):
        raise InstructionIntegrityViolation(
            agent_id=agent_id,
            expected_sha256="",
            actual_sha256="",
        )
    tool_names = tuple(sorted(str(name) for name in tools))
    tool_contracts_sha256 = _sha256(
        [_tool_contract(name, tools[name]) for name in tool_names]
    )
    system_message_sha256 = _sha256(
        {"role_name": role_name, "content": content}
    )
    canonical_sha256 = _sha256(
        {
            "agent_id": agent_id,
            "role_name": role_name,
            "content": content,
            "tool_names": tool_names,
            "tool_contracts_sha256": tool_contracts_sha256,
        }
    )
    return InstructionIntegrityRecordV1(
        agent_id=agent_id,
        role_name=role_name,
        tool_names=tool_names,
        tool_contracts_sha256=tool_contracts_sha256,
        system_message_sha256=system_message_sha256,
        canonical_sha256=canonical_sha256,
    )


def _tool_contract(name: str, tool: Any) -> dict[str, object]:
    schema_reader = getattr(tool, "get_openai_tool_schema", None)
    try:
        schema = schema_reader() if callable(schema_reader) else None
    except Exception as exc:
        raise InstructionIntegrityViolation(
            agent_id=None,
            expected_sha256="",
            actual_sha256="",
        ) from exc
    function = getattr(tool, "func", None)
    function_type = type(function if function is not None else tool)
    return {
        "name": name,
        "schema": schema,
        "binding_module": getattr(function, "__module__", function_type.__module__),
        "binding_qualname": getattr(
            function,
            "__qualname__",
            function_type.__qualname__,
        ),
    }


def _record_set_sha256(
    records: tuple[InstructionIntegrityRecordV1, ...],
) -> str:
    return _sha256(
        [(record.agent_id, record.canonical_sha256) for record in records]
    )


__all__ = [
    "InstructionIntegrityGuard",
    "InstructionIntegrityRecordV1",
    "InstructionIntegrityViolation",
]
