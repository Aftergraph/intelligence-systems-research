"""
test_study011_condition_conformance.py
=====================================

Condition isolation tests for STUDY-011 `apply_condition()`.

Pre-registered protocol invariant: conditions A, C, F, G must be
contamination-free. The pre-registration §2 (STUDY-011-LIVE-CROSS-PROVIDER-
PREREGISTRATION.md) commits to the following isolation rules:

  A: no assurance invoked (no verifier call, no gate)
  C: no assurance invoked, retry tracking only
  F: assurance must be invoked at least once (gate required)
  G: assurance + authority check + budget tracking all required

These tests pin the isolation rules with monkey-patched counters and
proxies. If `apply_condition()` is refactored and accidentally
introduces cross-contamination, these tests will fail loudly.

They are written to be deterministic and offline (no network).

ponytail: small, focused, single file — no fixtures, no parametrize
explosion, one assertion per behavior.
"""
import os
import sys
import json
import pytest

# Make the harness importable
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_REPO, "experiments", "live_benchmark"))

import run_study_011 as h  # noqa: E402


# ─── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def workload():
    """Minimal workload dict that satisfies the worker's lookups."""
    return {
        "workload_id": "S11-TEST-01",
        "task_family": "Software Engineering",
        "acceptance_criteria": ["return a string starting with 'DONE'"],
        "ground_truth": "DONE",
        "max_retries": 3,
        "max_recovery_attempts": 2,
        "token_budget": 1_000_000,
        "cost_budget_usd": 100.0,
    }


@pytest.fixture
def run_record():
    """A RunRecord with zero cost/tokens so budget assertions are inert."""
    return h.RunRecord(
        run_id="test-run-001",
        condition="A",
        workload_id="S11-TEST-01",
        provider_name="dialagram",
        exact_model_id="qwen-3.8-max",
        cost_usd=0.0,
        token_count_prompt=10,
        token_count_completion=10,
    )


@pytest.fixture
def completion_response():
    """Response that declares completion (matches acceptance criterion)."""
    return "DONE — task complete."


@pytest.fixture
def non_completion_response():
    """Response that does NOT declare completion."""
    return "I'm thinking about this. Let me try again."


# ─── Helpers: observability wrappers ───────────────────────────────────────


def _wrap_verifier():
    """Return (call_counter, wrapped_fn) where wrapped_fn tracks calls."""
    counter = {"n": 0, "pass_returned": True}

    def fake_verify(response, wl):
        counter["n"] += 1
        return {
            "pass": counter["pass_returned"],
            "receipt_hash": f"deadbeef{counter['n']:04d}",
            "diagnostic": None,
        }

    return counter, fake_verify


def _wrap_authority():
    """Return (call_counter, wrapped_fn) where wrapped_fn tracks calls."""
    counter = {"n": 0, "violations": []}

    def fake_authority(tool_calls):
        counter["n"] += 1
        return counter["violations"]

    return counter, fake_authority


# ─── Condition A: no assurance ─────────────────────────────────────────────


def test_condition_A_does_not_invoke_assurance(monkeypatch, workload, run_record, completion_response):
    counter, fake_verify = _wrap_verifier()
    monkeypatch.setattr(h, "verify_candidate_completion", fake_verify)

    out = h.apply_condition("A", completion_response, workload, run_record, h.ExecutionMode.LIVE_ONLY)

    assert counter["n"] == 0, "Condition A: verifier must not be called"
    assert out["assurance_invoked"] is False, "Condition A: assurance_invoked must be False"
    assert out["vsr_flag"] is False, "Condition A: no VSR receipt issued"
    assert out["mission_state_final"] == "VERIFIED", "Condition A: declared-complete -> VERIFIED"
    assert out["fcr_flag"] is False, "Condition A: fcr_flag always False (no gate)"


def test_condition_A_unknown_condition_raises(workload, run_record, completion_response):
    with pytest.raises(ValueError, match="Unknown condition"):
        h.apply_condition("Z", completion_response, workload, run_record, h.ExecutionMode.LIVE_ONLY)


# ─── Condition C: no assurance, retry tracking only ────────────────────────


def test_condition_C_does_not_invoke_assurance(monkeypatch, workload, run_record, completion_response):
    counter, fake_verify = _wrap_verifier()
    monkeypatch.setattr(h, "verify_candidate_completion", fake_verify)

    out = h.apply_condition("C", completion_response, workload, run_record, h.ExecutionMode.LIVE_ONLY)

    assert counter["n"] == 0, "Condition C: verifier must not be called"
    assert out["assurance_invoked"] is False, "Condition C: assurance_invoked must be False"
    assert out["vsr_flag"] is False, "Condition C: no VSR receipt issued"


def test_condition_C_tracks_retries_without_invoking_assurance(
    monkeypatch, workload, run_record, non_completion_response
):
    counter, fake_verify = _wrap_verifier()
    monkeypatch.setattr(h, "verify_candidate_completion", fake_verify)

    out = h.apply_condition("C", non_completion_response, workload, run_record, h.ExecutionMode.LIVE_ONLY)

    assert counter["n"] == 0, "Condition C: verifier must not be called even on failure path"
    assert out["assurance_invoked"] is False
    # retry_count is tracked (>= 0) but the gate never runs
    assert isinstance(out["retry_count"], int)
    assert out["retry_count"] >= 0


# ─── Condition F: assurance required ───────────────────────────────────────


def test_condition_F_invokes_assurance_on_completion(monkeypatch, workload, run_record, completion_response):
    counter, fake_verify = _wrap_verifier()
    counter["pass_returned"] = True
    monkeypatch.setattr(h, "verify_candidate_completion", fake_verify)

    out = h.apply_condition("F", completion_response, workload, run_record, h.ExecutionMode.LIVE_ONLY)

    assert counter["n"] >= 1, "Condition F: verifier must be called at least once"
    assert out["assurance_invoked"] is True
    assert out["mission_state_final"] == "VERIFIED"
    assert out["vsr_flag"] is True, "Condition F on PASS: VSR receipt must be issued"


def test_condition_F_cannot_bypass_when_verifier_fails(monkeypatch, workload, run_record, completion_response):
    """If the verifier says FAIL, mission_state must NOT be VERIFIED
    even though the agent declared completion. This pins the
    no-bypass invariant."""
    counter, fake_verify = _wrap_verifier()
    counter["pass_returned"] = False
    monkeypatch.setattr(h, "verify_candidate_completion", fake_verify)

    out = h.apply_condition("F", completion_response, workload, run_record, h.ExecutionMode.LIVE_ONLY)

    assert counter["n"] >= 1, "Condition F: verifier must run"
    assert out["mission_state_final"] != "VERIFIED", \
        "Condition F no-bypass: mission_state must NOT be VERIFIED when gate fails"
    assert out["fcr_flag"] is True, "Condition F on FAIL: declared_complete + !actual_success -> fcr_flag=True"
    assert out["vsr_flag"] is False, "Condition F on FAIL: no VSR receipt issued"


# ─── Condition G: assurance + authority + budget ───────────────────────────


def test_condition_G_all_three_gates_active(monkeypatch, workload, run_record, completion_response):
    v_counter, fake_verify = _wrap_verifier()
    v_counter["pass_returned"] = True
    a_counter, fake_authority = _wrap_authority()
    monkeypatch.setattr(h, "verify_candidate_completion", fake_verify)
    monkeypatch.setattr(h, "_check_authority", fake_authority)

    out = h.apply_condition("G", completion_response, workload, run_record, h.ExecutionMode.LIVE_ONLY)

    assert v_counter["n"] >= 1, "Condition G: verifier must run"
    assert a_counter["n"] >= 1, "Condition G: authority check must run"
    assert out["assurance_invoked"] is True
    assert out["vsr_flag"] is True


def test_condition_G_authority_hard_fails(monkeypatch, workload, run_record, completion_response):
    """If authority detects a violation, mission must FAILED even if
    verifier would pass. Pins the no-silent-disable invariant for the
    authority gate."""
    v_counter, fake_verify = _wrap_verifier()
    v_counter["pass_returned"] = True
    a_counter, fake_authority = _wrap_authority()
    a_counter["violations"] = ["UNAUTHORIZED: tool call out of scope"]
    monkeypatch.setattr(h, "verify_candidate_completion", fake_verify)
    monkeypatch.setattr(h, "_check_authority", fake_authority)

    out = h.apply_condition("G", completion_response, workload, run_record, h.ExecutionMode.LIVE_ONLY)

    assert a_counter["n"] >= 1
    assert "UNAUTHORIZED" in "; ".join(out["constraint_violations"]), \
        "Condition G: authority violation must be in constraint_violations"
    assert out["mission_state_final"] == "FAILED", \
        "Condition G no-silent-disable: authority violation -> FAILED, not VERIFIED"
    # FCR definition: declared_complete AND !actual_success. Authority violation
    # leaves the agent's declaration unchanged but actual_success=False, so fcr_flag
    # is correctly True. This is the protocol's intended signal: the agent SAID
    # it was done but the authority gate blocked it.
    assert out["fcr_flag"] is True, \
        "Condition G: authority-blocked run with declared_complete -> fcr_flag=True"


def test_condition_G_budget_overrun_records_violation(monkeypatch, workload, run_record, completion_response):
    """If token_budget is exceeded, violation must be recorded and the
    mission must FAILED."""
    v_counter, fake_verify = _wrap_verifier()
    v_counter["pass_returned"] = True
    a_counter, fake_authority = _wrap_authority()
    monkeypatch.setattr(h, "verify_candidate_completion", fake_verify)
    monkeypatch.setattr(h, "_check_authority", fake_authority)

    # Force a budget overrun: record says 100 tokens used, workload budget is 10
    run_record.token_count_prompt = 100
    run_record.token_count_completion = 0
    workload["token_budget"] = 10

    out = h.apply_condition("G", completion_response, workload, run_record, h.ExecutionMode.LIVE_ONLY)

    assert any("token budget exceeded" in v for v in out["constraint_violations"]), \
        f"Condition G: token-budget violation missing from {out['constraint_violations']}"
    assert out["mission_state_final"] == "FAILED", \
        "Condition G: budget violation -> FAILED"


# ─── Cross-condition: contamination detection ─────────────────────────────


def test_no_silent_assurance_in_A_or_C(monkeypatch, workload, run_record, completion_response):
    """Composite contamination check: across A and C, the verifier must
    be called ZERO times. A refactor that leaks the verifier into A or C
    (e.g. via a shared helper) will fail this test."""
    counter, fake_verify = _wrap_verifier()
    monkeypatch.setattr(h, "verify_candidate_completion", fake_verify)

    for cond in ("A", "C"):
        h.apply_condition(cond, completion_response, workload, run_record, h.ExecutionMode.LIVE_ONLY)

    assert counter["n"] == 0, (
        f"Contamination: verifier was called {counter['n']} times across A+C; "
        "A and C must be assurance-free."
    )


def test_assurance_in_F_and_G_always(monkeypatch, workload, run_record, completion_response):
    """Composite contamination check: F and G must ALWAYS invoke
    assurance at least once. A refactor that short-circuits the gate
    (e.g. on cached responses) will fail this test."""
    counter, fake_verify = _wrap_verifier()
    counter["pass_returned"] = True
    monkeypatch.setattr(h, "verify_candidate_completion", fake_verify)
    a_counter, fake_authority = _wrap_authority()
    monkeypatch.setattr(h, "_check_authority", fake_authority)

    for cond in ("F", "G"):
        h.apply_condition(cond, completion_response, workload, run_record, h.ExecutionMode.LIVE_ONLY)

    assert counter["n"] >= 2, (
        f"Missing assurance: verifier was called only {counter['n']} times "
        "across F+G; each must invoke at least once."
    )
