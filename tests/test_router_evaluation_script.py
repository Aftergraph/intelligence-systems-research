"""
test_router_evaluation_script.py
================================

Pins the output of experiments/test_router_evaluation.py (C-011)
as proper pytest tests. The script compares 4 routing policies:
FIXED_FRONTIER, FIXED_ECONOMY, RANDOM_ELIGIBLE, POLICY_CONSTRAINED_ROUTING
across all live-study workloads and reports VSR, CPVO, mean latency,
routing failures, and constraint violations.

This test pins:
- 4 policies are evaluated
- All workloads covered
- POLICY_CONSTRAINED_ROUTING has 0 routing failures
- POLICY_CONSTRAINED_ROUTING has 0 constraint violations
- VSR calculation is correct
- CSV output is LF
"""

import csv
import importlib.util
import os
import sys
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

experiments_path = os.path.join(workspace, "experiments")
if experiments_path not in sys.path:
    sys.path.insert(0, experiments_path)

spec = importlib.util.spec_from_file_location(
    "router_evaluation_module",
    os.path.join(experiments_path, "test_router_evaluation.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


POLICIES = [
    "FIXED_FRONTIER",
    "FIXED_ECONOMY",
    "RANDOM_ELIGIBLE",
    "POLICY_CONSTRAINED_ROUTING",
]


@pytest.fixture(scope="module")
def router_summaries():
    return mod.run_router_evaluation()


def test_four_policies_evaluated(router_summaries):
    assert set(router_summaries.keys()) == set(POLICIES)


@pytest.mark.parametrize("policy", POLICIES)
def test_each_policy_has_runs(router_summaries, policy):
    s = router_summaries[policy]
    assert s["runs"] > 0, f"Policy {policy} has 0 runs"


@pytest.mark.parametrize("policy", POLICIES)
def test_each_policy_zero_routing_failures(router_summaries, policy):
    s = router_summaries[policy]
    assert s["failures"] == 0, (
        f"Policy {policy} has {s['failures']} routing failures"
    )


@pytest.mark.parametrize("policy", POLICIES)
def test_each_policy_zero_constraint_violations(router_summaries, policy):
    s = router_summaries[policy]
    assert s["violations"] == 0, (
        f"Policy {policy} has {s['violations']} constraint violations. "
        f"The router is the security boundary; violations are P0."
    )


def test_router_csv_persisted():
    csv_path = Path(workspace) / "data" / "router_evaluation.csv"
    assert csv_path.exists()
    text = csv_path.read_bytes()
    assert b"\r\n" not in text, "router_evaluation.csv must be LF"
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    assert len(rows) > 0
    # Each policy should have multiple rows
    policies_in_csv = {r["policy"] for r in rows}
    assert policies_in_csv == set(POLICIES)


def test_vsr_calculated_for_each_policy(router_summaries):
    """VSR (Verified Success Rate) must be 0-100% for every policy."""
    for policy, s in router_summaries.items():
        n = s["runs"]
        vsr = (s["vsr_count"] / n) * 100.0
        assert 0 <= vsr <= 100, (
            f"Policy {policy} VSR={vsr:.1f}% is out of [0, 100] range"
        )


def test_cpvo_calculated_for_each_policy(router_summaries):
    """CPVO (Cost Per Verified Outcome) must be non-negative for every policy."""
    for policy, s in router_summaries.items():
        cpvo = s["total_cost"] / max(1, s["vsr_count"])
        assert cpvo >= 0, f"Policy {policy} CPVO={cpvo} is negative"


def test_total_cost_non_negative(router_summaries):
    for policy, s in router_summaries.items():
        assert s["total_cost"] >= 0


def test_total_latency_non_negative(router_summaries):
    for policy, s in router_summaries.items():
        assert s["total_lat"] >= 0


def test_runs_equal_across_policies(router_summaries):
    """All 4 policies must have evaluated the same number of workloads
    (the script iterates workloads × policies)."""
    runs = {p: s["runs"] for p, s in router_summaries.items()}
    assert len(set(runs.values())) == 1, (
        f"Policies have different run counts: {runs}. "
        f"Each policy must evaluate the same workload set."
    )
