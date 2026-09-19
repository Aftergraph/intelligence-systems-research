"""Decision-specific provider-state projection for JAR-EXP-0014.

System One decisions must not receive an undifferentiated agent-state blob. Each
eligible decision gets only fields relevant to that judgment. This reduces
cross-decision context contamination and limits accidental disclosure at the
provider boundary. Projection is advisory-input hygiene, not authority.
"""

import json
from typing import Any, Mapping

from .protocol import ELIGIBLE_DECISION_TYPES


class StateProjectionError(ValueError):
    pass


_COMMON_FIELDS = frozenset({"scenario"})

DECISION_STATE_FIELDS: dict[str, frozenset[str]] = {
    "route_model": _COMMON_FIELDS
    | frozenset({"task", "step", "requirements", "constraints", "ambiguity"}),
    "route_tool_family": _COMMON_FIELDS
    | frozenset(
        {"task", "step", "proposed_next_action", "available_tools", "approval_state"}
    ),
    "continue_loop": _COMMON_FIELDS
    | frozenset(
        {
            "acceptance_criteria",
            "current_evidence",
            "remaining_work",
            "blockers",
            "protected_remaining",
        }
    ),
    "result_sufficient": _COMMON_FIELDS
    | frozenset({"criterion", "acceptance_criteria", "current_evidence", "evidence"}),
    "needs_human": _COMMON_FIELDS
    | frozenset(
        {
            "proposed_next_action",
            "approval_state",
            "authority_state",
            "ambiguity",
            "protected_action",
            "financial_impact",
            "security_impact",
        }
    ),
    "risk_level": _COMMON_FIELDS
    | frozenset(
        {
            "proposed_next_action",
            "reversibility",
            "security_impact",
            "authority_impact",
            "external_side_effects",
            "financial_impact",
            "blast_radius",
        }
    ),
    "retryable_failure": _COMMON_FIELDS
    | frozenset(
        {
            "failure",
            "proposed_retry",
            "proposed_next_action",
            "side_effect_state",
            "idempotency_state",
            "requirements_changed",
            "authority_changed",
        }
    ),
    "evidence_conflict": _COMMON_FIELDS
    | frozenset(
        {
            "criterion",
            "observations",
            "evidence",
            "current_evidence",
            "source_freshness",
        }
    ),
}


def project_decision_state(
    *, decision_type: str, state: Mapping[str, Any]
) -> dict[str, Any]:
    """Return only state fields approved for one frozen decision class."""
    if decision_type not in ELIGIBLE_DECISION_TYPES:
        raise StateProjectionError(f"ineligible decision type: {decision_type}")
    if not isinstance(state, Mapping):
        raise StateProjectionError("System One state must be a mapping")

    allowed = DECISION_STATE_FIELDS[decision_type]
    projected = {key: state[key] for key in sorted(allowed) if key in state}
    if not projected:
        raise StateProjectionError(
            f"{decision_type}: state has no decision-relevant fields"
        )

    try:
        json.dumps(projected, allow_nan=False, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise StateProjectionError(
            f"{decision_type}: projected state is not strict JSON"
        ) from exc
    return projected
