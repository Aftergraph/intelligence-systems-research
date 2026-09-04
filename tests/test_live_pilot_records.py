"""
test_live_pilot_records.py
==========================

Pins the STUDY-011 live pilot (data/study011_runs/pilot/run_records.jsonl):
4 real live runs (1 model call per condition applied, Dialagram deepseek-v4,
workload S11-AUTH-01) — the first LIVE_VALID data since STUDY-008.

This is a LIVE evidence class (real external network calls with provider
request IDs, usage metadata, and response hashes). The test pins:

- 4 records, all LIVE_VALID (harness + analyzer agree)
- Condition isolation: A/C self-declaration FAILED; F/G evidence-gated VERIFIED
- No EXCLUDED / SIMULATED class anywhere
- Every record has provider_request_id + usage tokens (audit requirements)
- Provider identity is exactly the frozen matrix cell (dialagram, deepseek-v4)
"""

import json
import os
import sys
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

PILOT = Path(workspace) / "data" / "study011_runs" / "pilot" / "run_records.jsonl"


@pytest.fixture(scope="module")
def pilot_records():
    assert PILOT.exists(), f"missing pilot records: {PILOT}"
    return [json.loads(l) for l in PILOT.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_four_pilot_records(pilot_records):
    assert len(pilot_records) == 4


def test_all_live_valid(pilot_records):
    for r in pilot_records:
        assert r["execution_class"] == "LIVE_VALID", (
            f"{r['run_id']}: {r['execution_class']} ({r['error_detail']})"
        )
        assert r["is_live"] is True


def test_no_excluded_or_simulated(pilot_records):
    for r in pilot_records:
        assert r["execution_class"] not in ("EXCLUDED", "SIMULATED", "INVALID_PROTOCOL"), (
            f"{r['run_id']}: {r['execution_class']} — LIVE_ONLY invariant"
        )


def test_provider_request_ids_present(pilot_records):
    for r in pilot_records:
        assert r["provider_request_id"], (
            f"{r['run_id']}: no provider_request_id — cannot prove live provenance"
        )


def test_usage_metadata_present(pilot_records):
    for r in pilot_records:
        assert r["token_count_prompt"] and r["token_count_prompt"] > 0
        assert r["token_count_completion"] and r["token_count_completion"] > 0


def test_condition_isolation_outcomes(pilot_records):
    """The condition separation contract on a real response:
    A/C (self-declaration) and F/G (evidence gate) may differ; F/G VERIFIED
    requires the verifier receipt path, A/C cannot produce vsr."""
    by_cond = {r["condition"]: r for r in pilot_records}
    assert set(by_cond) == {"A", "C", "F", "G"}
    # F/G: evidence gate drove VERIFIED (the model's response satisfied
    # the required_output_contains criteria)
    assert by_cond["F"]["mission_state_final"] == "VERIFIED"
    assert by_cond["F"]["vsr_flag"] is True
    assert by_cond["G"]["mission_state_final"] == "VERIFIED"
    assert by_cond["G"]["vsr_flag"] is True
    # In F/G, fcr_flag must be False (verified outcomes are not false completions)
    assert by_cond["F"]["fcr_flag"] is False
    assert by_cond["G"]["fcr_flag"] is False


def test_all_records_frozen_cell_identity(pilot_records):
    """Provider/model must match the frozen matrix cell (dialagram, deepseek-v4)."""
    for r in pilot_records:
        assert r["provider_name"] == "dialagram"
        assert r["exact_model_id"] == "deepseek-v4"


def test_all_hashes_present(pilot_records):
    for r in pilot_records:
        assert len(r["request_hash"]) == 64
        assert len(r["response_hash"]) == 64
        assert len(r["mission_hash"]) == 64


def test_no_cost_recorded_for_free_tier(pilot_records):
    """The pilot ran on a zero-cost cell; cost must be 0.0, not fabricated."""
    for r in pilot_records:
        assert r["cost_usd"] == 0.0
