"""Fail-closed routing policy for JAR-EXP-0014.

This module is research-only. It decides whether a typed System One answer may
be consumed by the experiment harness. It never grants execution authority and
it never establishes verification.
"""

from dataclasses import dataclass
from typing import Literal

DecisionKind = Literal["noul", "choice", "score"]
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
    authority_bypassed: Literal[False] = False


def route_system_one_decision(
    *,
    decision_type: str,
    answer_kind: str,
    confidence: float | None,
    transport_ok: bool,
    schema_ok: bool,
    authority_sensitive_ambiguity: bool,
    evidence_conflict: bool,
    policy: DecisionPolicy,
) -> RoutingDecision:
    """Return the experiment routing result without authorizing execution.

    Precedence is deliberately fail-closed:
    ineligible/invalid input -> fallback;
    authority ambiguity or evidence conflict -> escalation;
    low confidence -> fallback;
    otherwise accept the typed decision for downstream *advisory* use.
    """
    if decision_type not in ELIGIBLE_DECISION_TYPES:
        return RoutingDecision("fallback", True, "ineligible_decision_type")

    if answer_kind not in {"noul", "choice", "score"}:
        return RoutingDecision("fallback", True, "invalid_answer_kind")

    if not transport_ok:
        return RoutingDecision("fallback", True, "transport_failure")

    if not schema_ok:
        return RoutingDecision("fallback", True, "schema_failure")

    if authority_sensitive_ambiguity:
        return RoutingDecision("escalate", True, "authority_sensitive_ambiguity")

    if evidence_conflict:
        return RoutingDecision("escalate", True, "evidence_conflict")

    if confidence is None or not 0.0 <= confidence <= 1.0:
        return RoutingDecision("fallback", True, "invalid_confidence")

    if confidence < policy.confidence_threshold:
        return RoutingDecision("fallback", True, "below_confidence_threshold")

    return RoutingDecision("accept", False, None)
