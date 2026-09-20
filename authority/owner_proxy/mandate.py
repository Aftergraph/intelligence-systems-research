"""Mandate evaluation: the two-tier fence (spec §1 decision 4, §5).

``evaluate_mandate`` is the single decision function. Given the owner-signed
record, a proposed action, the action's real bindings, and a pinned ``now``, it
returns one of three verdicts:

  ALLOW_ROUTINE     -- the action is in scope, its matter is not reserved, and
                       its bindings are within the mandate's ceilings. The spine
                       may act under the standing mandate.
  REFUSE_RESERVED   -- the action maps to a matter named in the record's
                       reserved_matters[]. The standing mandate does NOT cover
                       it; a fresh per-act owner confirmation is required.
  REFUSE_INVALID    -- the mandate itself is unusable for this act (expired,
                       not-yet-valid, revoked, out of scope, or a binding that
                       exceeds the ceiling). reason names which.

The temporal + scope shape mirrors ``authority.evaluator.AuthorityEvaluator``
(revoked / valid_from / expires_at / denied-before-allowed), and the scope is an
ALLOWLIST: an unrecognized action or one outside ``scope`` is out_of_scope, which
is what keeps "general proxy" from silently becoming "unbounded" (spec §4).

Pure and deterministic: no crypto, no I/O, no clock reads (``now`` is a
parameter so tests pin it -- spec §8 Clock).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

ALLOW_ROUTINE = "ALLOW_ROUTINE"
REFUSE_RESERVED = "REFUSE_RESERVED"
REFUSE_INVALID = "REFUSE_INVALID"

# Action taxonomy. Each action belongs to exactly one "matter"; reserved_matters
# carves denies out of the scope allowlist at matter granularity. Unknown actions
# are refused out_of_scope (fail-closed default).
ACTION_MATTER: dict[str, str] = {
    "SIGN_CALIBRATION_GATE": "CALIBRATION_APPROVAL",
    "RATIFY_ADR": "ADR_RATIFICATION",
    "ANSWER_ESCALATION": "ESCALATION",
    "DISPATCH_SUBAGENT": "DISPATCH",
    "MERGE_BRANCH": "BRANCH_MERGE",
    "RAISE_BUDGET": "BUDGET_RAISE",
    "BREAK_MANIFEST_PIN": "MANIFEST_PIN",
    "RUN_HOLDOUT_BEFORE_CALIBRATION": "HOLDOUT_ORDERING",
    "EDIT_FROZEN_0014_RECORD": "FROZEN_0014_RECORD",
}


@dataclass(frozen=True)
class MandateDecision:
    verdict: str
    reason: str | None = None


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def evaluate_mandate(
    record: dict[str, Any],
    action: str,
    bindings: dict[str, Any],
    now: datetime,
    *,
    revoked: bool = False,
) -> MandateDecision:
    """Decide ALLOW_ROUTINE / REFUSE_RESERVED / REFUSE_INVALID for one act."""
    # 1. Recognized action? (allowlist default -- unrecognized == refused)
    if action not in ACTION_MATTER:
        return MandateDecision(REFUSE_INVALID, "out_of_scope")

    # 2. Temporal validity (mirrors AuthorityEvaluator valid_from/expires_at).
    not_before = record.get("not_before")
    expires_at = record.get("expires_at")
    try:
        if isinstance(not_before, str) and not_before.strip():
            if now < _parse(not_before):
                return MandateDecision(REFUSE_INVALID, "mandate_not_yet_valid")
        if isinstance(expires_at, str) and expires_at.strip():
            if now > _parse(expires_at):
                return MandateDecision(REFUSE_INVALID, "mandate_expired")
    except ValueError:
        return MandateDecision(REFUSE_INVALID, "mandate_timestamp_invalid")

    # 3. Revocation (checked live by the caller; never cached -- spec §8).
    if revoked:
        return MandateDecision(REFUSE_INVALID, "mandate_revoked")

    # 4. Scope allowlist.
    scope = record.get("scope") or []
    if action not in scope:
        return MandateDecision(REFUSE_INVALID, "out_of_scope")

    # 5. Reserved-matter fence.
    matter = ACTION_MATTER[action]
    reserved = record.get("reserved_matters") or []
    if matter in reserved:
        return MandateDecision(REFUSE_RESERVED, matter)

    # 6. Binding ceilings -- a valid mandate for THIS act cannot sign THAT act.
    cost = bindings.get("cost_usd")
    ceiling = record.get("budget_ceiling_usd")
    if cost is not None and ceiling is not None:
        try:
            if float(cost) > float(ceiling):
                return MandateDecision(REFUSE_INVALID, "binding_cost_ceiling")
        except (TypeError, ValueError):
            return MandateDecision(REFUSE_INVALID, "binding_cost_ceiling")

    experiment_binding = record.get("experiment_binding")
    if isinstance(experiment_binding, dict):
        for key in ("manifest", "model", "calls"):
            if key in experiment_binding and bindings.get(key) != experiment_binding[key]:
                return MandateDecision(REFUSE_INVALID, f"binding_{key}_mismatch")

    return MandateDecision(ALLOW_ROUTINE)