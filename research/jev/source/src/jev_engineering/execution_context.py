from __future__ import annotations

from dataclasses import asdict, dataclass
import time
import uuid
from typing import Any


@dataclass(frozen=True, slots=True)
class WorksExecutionContext:
    execution_context_id: str
    trace_id: str
    mission_id: str
    node_id: str
    principal: str
    parent_execution_context_id: str | None = None
    created_at: float = 0.0

    def __post_init__(self) -> None:
        for name, value in (
            ("execution_context_id", self.execution_context_id),
            ("trace_id", self.trace_id),
            ("mission_id", self.mission_id),
            ("node_id", self.node_id),
            ("principal", self.principal),
        ):
            if not str(value).strip():
                raise ValueError(f"{name} must be non-empty")

    @classmethod
    def create(
        cls,
        *,
        mission_id: str,
        node_id: str,
        principal: str,
        trace_id: str | None = None,
        parent_execution_context_id: str | None = None,
        execution_context_id: str | None = None,
        created_at: float | None = None,
    ) -> "WorksExecutionContext":
        return cls(
            execution_context_id=execution_context_id or "exec_" + uuid.uuid4().hex[:24],
            trace_id=trace_id or "trace_" + uuid.uuid4().hex[:24],
            mission_id=mission_id,
            node_id=node_id,
            principal=principal,
            parent_execution_context_id=parent_execution_context_id,
            created_at=time.time() if created_at is None else float(created_at),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WorksExecutionContext":
        return cls(
            execution_context_id=str(payload.get("execution_context_id") or ""),
            trace_id=str(payload.get("trace_id") or ""),
            mission_id=str(payload.get("mission_id") or ""),
            node_id=str(payload.get("node_id") or ""),
            principal=str(payload.get("principal") or ""),
            parent_execution_context_id=(
                str(payload["parent_execution_context_id"])
                if payload.get("parent_execution_context_id") is not None
                else None
            ),
            created_at=float(payload.get("created_at", 0.0)),
        )
