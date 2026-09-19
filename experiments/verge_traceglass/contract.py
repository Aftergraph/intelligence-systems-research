from __future__ import annotations

from dataclasses import dataclass
from typing import Any


REQUIRED_POLICY_FIELDS = (
    "confidence_threshold",
    "verification_depth",
    "retry_ceiling",
)

REQUIRED_CONTEXT_FIELDS = (
    "min_confidence",
    "min_verification",
    "min_retries",
)

REQUIRED_OUTCOME_FIELDS = (
    "verified_success",
    "false_completion",
    "unauthorized_actions",
    "evidence_integrity_failures",
    "cost",
    "latency",
    "human_interventions",
)

REQUIRED_PROVENANCE_FIELDS = (
    "source_artifact",
    "source_hash",
)


@dataclass(frozen=True)
class TraceReadiness:
    source: str
    evidence_class: str
    admissible: bool
    missing_fields: tuple[str, ...]
    reason: str


def audit_record(source: str, evidence_class: str, record: dict[str, Any]) -> TraceReadiness:
    required = (
        ("run_id", "workload_id")
        + REQUIRED_POLICY_FIELDS
        + REQUIRED_CONTEXT_FIELDS
        + REQUIRED_OUTCOME_FIELDS
        + REQUIRED_PROVENANCE_FIELDS
    )
    missing = tuple(
        field
        for field in required
        if field not in record or record[field] is None
    )

    blocked_class = evidence_class in {
        "SIMULATION_ONLY",
        "FIXTURE_ONLY",
        "INFRASTRUCTURE_ONLY",
    }

    if blocked_class:
        return TraceReadiness(
            source=source,
            evidence_class=evidence_class,
            admissible=False,
            missing_fields=missing,
            reason=f"evidence class {evidence_class} is not out-of-simulator execution evidence",
        )

    if missing:
        return TraceReadiness(
            source=source,
            evidence_class=evidence_class,
            admissible=False,
            missing_fields=missing,
            reason="required pre-action policy/context or fixed outcome/provenance fields are missing",
        )

    return TraceReadiness(
        source=source,
        evidence_class="TRACE_COMPATIBLE",
        admissible=True,
        missing_fields=(),
        reason="all frozen Headroom trace-corpus fields are present",
    )
