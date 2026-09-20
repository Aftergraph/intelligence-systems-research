"""Truth-table units for ``authority.owner_proxy.mandate.evaluate_mandate``.

Spec §9 "Truth-table units": every combination of (scope, tier, expiry, revocation,
bindings) -> expected verdict. Pure and deterministic; no crypto, no I/O, no clock
reads (``now`` is a parameter). This is the two-tier fence made testable.
"""

from __future__ import annotations

from datetime import datetime, timezone

from authority.owner_proxy.mandate import (
    ALLOW_ROUTINE,
    REFUSE_INVALID,
    REFUSE_RESERVED,
    evaluate_mandate,
)

NOW = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
PIN = "dc5d7a94f333908abf09aebe1ca1dbf08f965e604eb2919d0b7a9ca70e149762"


def _record(**over):
    base = {
        "schema_version": "aftergraph.owner-proxy-delegation/0.1",
        "principal": "JonasAbde <147070826+JonasAbde@users.noreply.github.com>",
        "delegate": "agent:owner-authority",
        "not_before": "2026-09-20T00:00:00+00:00",
        "expires_at": "2026-12-19T23:59:59+00:00",
        "scope": ["SIGN_CALIBRATION_GATE", "RATIFY_ADR", "MERGE_BRANCH"],
        "reserved_matters": ["BRANCH_MERGE", "MANIFEST_PIN"],
        "budget_ceiling_usd": 5.38,
        "experiment_binding": {"manifest": PIN, "model": "jev-1.13.0", "calls": 1952},
    }
    base.update(over)
    return base


def _bindings(**over):
    b = {"manifest": PIN, "model": "jev-1.13.0", "calls": 1952, "cost_usd": 5.38}
    b.update(over)
    return b


def test_routine_calibration_act_is_allowed():
    dec = evaluate_mandate(_record(), "SIGN_CALIBRATION_GATE", _bindings(), NOW)
    assert dec.verdict == ALLOW_ROUTINE
    assert dec.reason is None


def test_cost_equal_to_ceiling_is_allowed_boundary():
    # 5.38 == 5.38 must pass (the fence is `>`, not `>=`), so Gate B is routine.
    dec = evaluate_mandate(_record(), "SIGN_CALIBRATION_GATE", _bindings(cost_usd=5.38), NOW)
    assert dec.verdict == ALLOW_ROUTINE


def test_reserved_matter_is_refused_reserved_not_invalid():
    # MERGE_BRANCH maps to matter BRANCH_MERGE, which is in reserved_matters.
    dec = evaluate_mandate(_record(), "MERGE_BRANCH", _bindings(), NOW)
    assert dec.verdict == REFUSE_RESERVED
    assert dec.reason == "BRANCH_MERGE"


def test_unrecognized_action_is_out_of_scope_allowlist_default():
    dec = evaluate_mandate(_record(), "FLY_A_KITE", _bindings(), NOW)
    assert dec.verdict == REFUSE_INVALID
    assert dec.reason == "out_of_scope"


def test_action_absent_from_scope_allowlist_is_out_of_scope():
    rec = _record(scope=["RATIFY_ADR"])  # SIGN_CALIBRATION_GATE dropped
    dec = evaluate_mandate(rec, "SIGN_CALIBRATION_GATE", _bindings(), NOW)
    assert dec.verdict == REFUSE_INVALID
    assert dec.reason == "out_of_scope"


def test_expired_mandate_is_refused():
    rec = _record(expires_at="2026-09-19T00:00:00+00:00")  # before NOW
    dec = evaluate_mandate(rec, "SIGN_CALIBRATION_GATE", _bindings(), NOW)
    assert dec.verdict == REFUSE_INVALID
    assert dec.reason == "mandate_expired"


def test_not_yet_valid_mandate_is_refused():
    rec = _record(not_before="2026-09-21T00:00:00+00:00")  # after NOW
    dec = evaluate_mandate(rec, "SIGN_CALIBRATION_GATE", _bindings(), NOW)
    assert dec.verdict == REFUSE_INVALID
    assert dec.reason == "mandate_not_yet_valid"


def test_revoked_flag_is_refused_even_when_otherwise_valid():
    dec = evaluate_mandate(_record(), "SIGN_CALIBRATION_GATE", _bindings(), NOW, revoked=True)
    assert dec.verdict == REFUSE_INVALID
    assert dec.reason == "mandate_revoked"


def test_cost_above_ceiling_is_binding_refusal():
    dec = evaluate_mandate(_record(), "SIGN_CALIBRATION_GATE", _bindings(cost_usd=10.0), NOW)
    assert dec.verdict == REFUSE_INVALID
    assert dec.reason == "binding_cost_ceiling"


def test_manifest_binding_drift_is_refused():
    dec = evaluate_mandate(_record(), "SIGN_CALIBRATION_GATE", _bindings(manifest="a" * 64), NOW)
    assert dec.verdict == REFUSE_INVALID
    assert dec.reason == "binding_manifest_mismatch"


def test_model_binding_drift_is_refused():
    dec = evaluate_mandate(_record(), "SIGN_CALIBRATION_GATE", _bindings(model="jev-9.9.9"), NOW)
    assert dec.verdict == REFUSE_INVALID
    assert dec.reason == "binding_model_mismatch"


def test_calls_binding_drift_is_refused():
    dec = evaluate_mandate(_record(), "SIGN_CALIBRATION_GATE", _bindings(calls=1), NOW)
    assert dec.verdict == REFUSE_INVALID
    assert dec.reason == "binding_calls_mismatch"


def test_unparseable_mandate_timestamp_is_refused_fail_closed():
    rec = _record(expires_at="not-a-timestamp")
    dec = evaluate_mandate(rec, "SIGN_CALIBRATION_GATE", _bindings(), NOW)
    assert dec.verdict == REFUSE_INVALID
    assert dec.reason == "mandate_timestamp_invalid"


def test_reserved_check_precedes_binding_check_tier_semantics():
    # A reserved matter is REFUSE_RESERVED regardless of bindings (the fence is about
    # the KIND of act, not its numbers).
    dec = evaluate_mandate(_record(), "MERGE_BRANCH", _bindings(cost_usd=999.0), NOW)
    assert dec.verdict == REFUSE_RESERVED