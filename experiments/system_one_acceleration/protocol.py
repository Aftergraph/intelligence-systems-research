"""Fail-closed routing policy for JAR-EXP-0014.

This module is research-only. It decides whether a typed System One answer may
be consumed by the experiment harness. It never grants execution authority and
it never establishes verification.
"""

from dataclasses import dataclass
from typing import Literal

Route = Literal["accept", "fallback", "escalate"]

ELIGIBLE_DECISION_TYPES = frozenset(
    {
        "route_model",
        "route_tool_family",
        "continue_loop",
        "result_sufficient",
        "needs_human",
        "risk_level",
        "retryable_failure",
        "evidence_conflict",
    }
)


@dataclass(frozen=True)
class DecisionPolicy:
    confidence_threshold: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be within [0, 1]")


@dataclass(frozen=True)
class RoutingDecision:
    decision: Route
    fallback_used: bool
    fallback_reason: str | None
    effective_confidence: float | None
    authority_bypassed: Literal[False] = False


def effective_confidence(
    *, answer_kind: str, answer_value: object, reported_confidence: float | None
) -> float | None:
    """Normalize Jev answer certainty without fabricating a Noul confidence field."""
    if answer_kind == "noul":
        if isinstance(answer_value, bool) or not isinstance(answer_value, (int, float)):
            return None
        probability = float(answer_value)
        if not 0.0 <= probability <= 1.0:
            return None
        return 2.0 * abs(probability - 0.5)

    if answer_kind in {"choice", "score"}:
        if reported_confidence is None or not 0.0 <= reported_confidence <= 1.0:
            return None
        return float(reported_confidence)

    return None


def route_system_one_decision(
    *,
    decision_type: str,
    answer_kind: str,
    answer_value: object,
    reported_confidence: float | None,
    transport_ok: bool,
    schema_ok: bool,
    authority_sensitive_ambiguity: bool,
    evidence_conflict: bool,
    policy: DecisionPolicy,
) -> RoutingDecision:
    """Return an advisory routing result; never authorize execution."""
    if decision_type not in ELIGIBLE_DECISION_TYPES:
        return RoutingDecision("fallback", True, "ineligible_decision_type", None)

    if answer_kind not in {"noul", "choice", "score"}:
        return RoutingDecision("fallback", True, "invalid_answer_kind", None)

    if not transport_ok:
        return RoutingDecision("fallback", True, "transport_failure", None)

    if not schema_ok:
        return RoutingDecision("fallback", True, "schema_failure", None)

    if authority_sensitive_ambiguity:
        return RoutingDecision(
            "escalate", True, "authority_sensitive_ambiguity", None
        )

    if evidence_conflict:
        return RoutingDecision("escalate", True, "evidence_conflict", None)

    confidence = effective_confidence(
        answer_kind=answer_kind,
        answer_value=answer_value,
        reported_confidence=reported_confidence,
    )
    if confidence is None:
        return RoutingDecision("fallback", True, "invalid_confidence", None)

    if confidence < policy.confidence_threshold:
        return RoutingDecision(
            "fallback", True, "below_confidence_threshold", confidence
        )

    return RoutingDecision("accept", False, None, confidence)
