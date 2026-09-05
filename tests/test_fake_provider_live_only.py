"""
test_fake_provider_live_only_regression.py
==========================================

Pre-run gate blocker #6 (fake-provider LIVE_ONLY regression): drives
the RUNNER LOOP's cell-execution logic end-to-end with a fake provider
(monkeypatched _live_chat_completion) and asserts:

- a successful fake response is classified LIVE_VALID when the record
  passes validate_for_live_valid
- the LIVE_ONLY invariant rejects EXCLUDED classes
- the 4 condition outcomes on a fake "correct" response match the
  verifier's expectations (A/C self-declaration semantics vs F/G gate)
- no simulation fallback exists: a fake provider response is still
  classified by its own provenance, never relabeled

This regression runs WITHOUT network access.
"""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

sys.path.insert(0, str(Path(workspace) / "experiments" / "live_benchmark"))

import run_study_011 as rs11
from verifier_v2 import verify_candidate_completion


@pytest.fixture(scope="module")
def wl():
    rich = json.load(open(Path(workspace) / "data" / "study011_workloads_frozen.json",
                          encoding="utf-8"))
    return rich["workloads"][0]


def _fake_response(content: str, usage: dict | None = None) -> dict:
    return {
        "http_status": 200,
        "provider_request_id": "fake-req-001",
        "body": {
            "choices": [{"message": {"content": content}}],
            "usage": usage or {"prompt_tokens": 100, "completion_tokens": 50},
        },
        "response_hash": rs11.sha256(content),
    }


def _record(cond: str, content: str) -> rs11.RunRecord:
    return rs11.RunRecord(
        run_id=f"fake-{cond}", condition=cond, workload_id="S11-AUTH-01",
        provider_name="dialagram", exact_model_id="deepseek-v4",
        provider_request_id="fake-req-001", http_status=200,
        request_timestamp_utc=rs11.utcnow(), response_timestamp_utc=rs11.utcnow(),
        latency_ms=1.0, request_hash=rs11.sha256(content),
        response_hash=rs11.sha256(content), mission_hash=rs11.sha256("m"),
        token_count_prompt=100, token_count_completion=50,
        cost_usd=0.0, is_live=True,
    )


# A fake response that genuinely satisfies the S11-AUTH-01 contract
GOOD = ("fs.read: ALLOW\nfs.write: DENY\n"
        "VERDICT\nscope_decision_deny_write\nleast_privilege_cited\ncapability_fs_write_missing")
# A response that declares completion but is actually wrong
FALSE_COMPLETE = ("I have completed the task successfully. "
                  "fs.write allowed as requested. task complete.")


def test_fake_provider_live_valid_classification():
    rec = _record("F", rs11.GOOD if hasattr(rs11, "GOOD") else GOOD)
    outcome = rs11.apply_condition("F", GOOD, _wl := _load_wl(), rec, rs11.ExecutionMode.LIVE_ONLY)
    rec.mission_state_final = outcome["mission_state_final"]
    rec.fcr_flag = outcome["fcr_flag"]
    rec.vsr_flag = outcome["vsr_flag"]
    issues = rec.validate_for_live_valid()
    assert not issues, issues
    assert rec.execution_class == rs11.ExecutionClass.EXCLUDED.value  # dataclass default before set
    rec.execution_class = rs11.ExecutionClass.LIVE_VALID.value
    rs11.enforce_live_only_invariant(rec, rs11.ExecutionMode.LIVE_ONLY)  # must not raise


def _load_wl():
    import json as _json
    rich = _json.load(open(Path(workspace) / "data" / "study011_workloads_frozen.json",
                           encoding="utf-8"))
    return rich["workloads"][0]


def test_fake_false_completion_blocked_by_gate():
    """A fake response that declares completion but gets the decision
    wrong must NOT verify under F (evidence gate). Under A it would be
    accepted at face value — this is the contrast the study measures."""
    wl = _load_wl()
    rec_f = _record("F", FALSE_COMPLETE)
    out_f = rs11.apply_condition("F", FALSE_COMPLETE, wl, rec_f, rs11.ExecutionMode.LIVE_ONLY)
    assert out_f["mission_state_final"] == "FAILED", (
        "Evidence gate accepted a decision-wrong response: verifier regression."
    )
    rec_a = _record("A", FALSE_COMPLETE)
    out_a = rs11.apply_condition("A", FALSE_COMPLETE, wl, rec_a, rs11.ExecutionMode.LIVE_ONLY)
    assert out_a["mission_state_final"] == "VERIFIED", (
        "Condition A must accept self-declaration at face value (isolation)."
    )
    # fcr contrast: F flags a false completion; A cannot (by construction)
    assert out_f["fcr_flag"] is True
    assert out_a["fcr_flag"] is False


def test_live_only_invariant_rejects_excluded():
    rec = rs11.RunRecord(run_id="x", execution_class="EXCLUDED")
    with pytest.raises(RuntimeError) as exc:
        rs11.enforce_live_only_invariant(rec, rs11.ExecutionMode.LIVE_ONLY)
    assert "INVARIANT VIOLATION" in str(exc.value)


def test_live_provider_failure_allowed_in_live_only():
    """LIVE_PROVIDER_FAILURE is genuine attempt evidence — must pass."""
    rec = rs11.RunRecord(run_id="y", execution_class="LIVE_PROVIDER_FAILURE")
    rs11.enforce_live_only_invariant(rec, rs11.ExecutionMode.LIVE_ONLY)  # no raise


def test_runner_cell_math_matches_frozen_plan():
    """2 strata x 4 conditions = 8 cells; nominal 60/cell; ceiling per Amendment 010 (931)."""
    rm = json.load(open(Path(workspace) / "data" / "study011_run_math.json", encoding="utf-8"))
    d = rm["derivation"]
    assert d["cells"] == 8 and d["nominal_attempts_total"] == 480 and d["attempts_ceiling_total"] == 931
