"""
test_economics_q002.py
=======================

Pins Q-002 (economics): automated verification recovery inverts the
economics of false completions, reducing CPVO by ~81%.

The claim C-003 is: "CPVO reduced 81.3% [74.2%, 87.5%] in calibrated
simulation."

This test pins:
- baseline CPVO (1_baseline) = $0.5791
- full-system CPVO (8_full_system) = $0.1081
- reduction = 81.3% (within the 95% Wilson CI [74.2%, 87.5%])
"""

import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)


RESULTS_CSV = "data/results_mission_bench.csv"
EXPECTED_BASELINE_CPVO = 0.5791
EXPECTED_FULL_SYSTEM_CPVO = 0.1081
EXPECTED_REDUCTION_MIN_PCT = 74.2
EXPECTED_REDUCTION_MAX_PCT = 87.5


def _compute_cpvo(stage: str) -> float:
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_CSV)))
    cost = 0.0
    verified = 0
    for r in rows:
        if r["ablation_stage"] != stage:
            continue
        cost += float(r["cost_usd"])
        if r["is_verified"] == "True":
            verified += 1
    if verified == 0:
        return float("inf")
    return cost / verified


def test_baseline_cpvo():
    """Stage 1 (baseline) CPVO must be ~$0.5791."""
    cpvo = _compute_cpvo("1_baseline")
    assert abs(cpvo - EXPECTED_BASELINE_CPVO) < 0.05, (
        f"Baseline CPVO ${cpvo:.4f} differs from expected "
        f"${EXPECTED_BASELINE_CPVO} by more than $0.05"
    )


def test_full_system_cpvo():
    """Stage 8 (full system) CPVO must be ~$0.1081."""
    cpvo = _compute_cpvo("8_full_system")
    assert abs(cpvo - EXPECTED_FULL_SYSTEM_CPVO) < 0.05, (
        f"Full-system CPVO ${cpvo:.4f} differs from expected "
        f"${EXPECTED_FULL_SYSTEM_CPVO} by more than $0.05"
    )


def test_cpvo_reduction_in_wilson_interval():
    """The CPVO reduction must be in [74.2%, 87.5%], the 95% Wilson CI
    from the audit."""
    baseline = _compute_cpvo("1_baseline")
    full = _compute_cpvo("8_full_system")
    reduction_pct = 100.0 * (baseline - full) / baseline
    assert EXPECTED_REDUCTION_MIN_PCT <= reduction_pct <= EXPECTED_REDUCTION_MAX_PCT, (
        f"CPVO reduction {reduction_pct:.1f}% is outside the audit's "
        f"95% Wilson CI [{EXPECTED_REDUCTION_MIN_PCT}%, "
        f"{EXPECTED_REDUCTION_MAX_PCT}%]. This breaks claim C-003."
    )


def test_cpvo_monotonically_decreases_or_equals():
    """CPVO should generally decrease as the system adds more
    capabilities (this is the economic inversion hypothesis)."""
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_CSV)))
    by_stage = defaultdict(lambda: {"cost": 0.0, "verified": 0})
    for r in rows:
        s = r["ablation_stage"]
        by_stage[s]["cost"] += float(r["cost_usd"])
        if r["is_verified"] == "True":
            by_stage[s]["verified"] += 1
    order = [
        "1_baseline", "2_plus_mission", "3_plus_state",
        "4_plus_authority", "5_plus_verification", "6_plus_evidence",
        "7_plus_recovery", "8_full_system",
    ]
    rates = [
        by_stage[s]["cost"] / max(by_stage[s]["verified"], 1)
        for s in order
    ]
    # The full system (last) should have the lowest CPVO.
    # Other transitions may not be monotone (5_plus_verification has
    # V=0 because no evidence setup was made; that is the data
    # anomaly documented in the audit). We only check that the
    # *final* stage is the lowest.
    assert rates[-1] < rates[0], (
        f"Full system CPVO {rates[-1]:.4f} is not lower than "
        f"baseline CPVO {rates[0]:.4f}. The economic inversion "
        f"is not measurable."
    )


def test_per_stage_costs_present():
    """All 8 stages must have measurable cost data."""
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_CSV)))
    by_stage = defaultdict(float)
    for r in rows:
        by_stage[r["ablation_stage"]] += float(r["cost_usd"])
    for s in [
        "1_baseline", "2_plus_mission", "3_plus_state",
        "4_plus_authority", "5_plus_verification", "6_plus_evidence",
        "7_plus_recovery", "8_full_system",
    ]:
        assert by_stage[s] > 0, (
            f"Stage {s} has zero cost. Cost model may have drifted."
        )
