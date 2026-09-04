"""
test_router_evaluation_pinning.py
==================================

Pins the STUDY-008 router evaluation. The claim C-011 is:
"Policy-constrained scored routing matches frontier model performance
at lower cost in simulated routing benchmark — VSR matches frontier
(84.0% vs 84.0%) with 22.2% lower cost and 17.2% lower latency;
0 constraint violations."

The router data has 4 policies x 25 tasks = 100 runs. We pin:
- 4 policies (FIXED_FRONTIER, FIXED_ECONOMY, RANDOM_ELIGIBLE,
  POLICY_CONSTRAINED_ROUTING)
- 25 tasks per policy
- FIXED_FRONTIER VSR == POLICY_CONSTRAINED_ROUTING VSR (both 84%)
- POLICY_CONSTRAINED_ROUTING cost is 22.2% lower than FIXED_FRONTIER
- POLICY_CONSTRAINED_ROUTING latency is 17.2% lower than FIXED_FRONTIER
- 0 constraint violations across all policies
"""

import csv
import os
import sys
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)


RESULTS_PATH = "data/router_evaluation.csv"
EXPECTED_POLICIES = {
    "FIXED_FRONTIER",
    "FIXED_ECONOMY",
    "RANDOM_ELIGIBLE",
    "POLICY_CONSTRAINED_ROUTING",
}
EXPECTED_TASKS_PER_POLICY = 25


def test_results_csv_exists():
    p = Path(workspace) / RESULTS_PATH
    assert p.exists(), f"{RESULTS_PATH} missing"


def test_results_has_4_policies():
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_PATH)))
    policies = {r["policy"] for r in rows}
    assert policies == EXPECTED_POLICIES, (
        f"Policies {policies} != expected {EXPECTED_POLICIES}"
    )


def test_results_has_25_per_policy():
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_PATH)))
    by_policy = {}
    for r in rows:
        by_policy.setdefault(r["policy"], 0)
        by_policy[r["policy"]] += 1
    for p in EXPECTED_POLICIES:
        n = by_policy.get(p, 0)
        assert n == EXPECTED_TASKS_PER_POLICY, (
            f"Policy {p} has {n} tasks, expected {EXPECTED_TASKS_PER_POLICY}"
        )


def test_scored_routing_matches_frontier_vsr():
    """POLICY_CONSTRAINED_ROUTING VSR must equal FIXED_FRONTIER VSR
    (both 84.0% per the audit)."""
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_PATH)))
    vsr = {}
    for p in EXPECTED_POLICIES:
        p_rows = [r for r in rows if r["policy"] == p]
        vsr[p] = sum(1 for r in p_rows if r["verified_success"] == "True")
    assert vsr["FIXED_FRONTIER"] == vsr["POLICY_CONSTRAINED_ROUTING"], (
        f"VSR(FIXED_FRONTIER)={vsr['FIXED_FRONTIER']} != "
        f"VSR(POLICY_CONSTRAINED_ROUTING)={vsr['POLICY_CONSTRAINED_ROUTING']}. "
        f"Claim C-011 requires VSR match."
    )


def test_scored_routing_is_22pct_cheaper():
    """POLICY_CONSTRAINED_ROUTING cost must be ~22.2% lower than
    FIXED_FRONTIER cost (per C-011)."""
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_PATH)))
    cost = {}
    for p in ("FIXED_FRONTIER", "POLICY_CONSTRAINED_ROUTING"):
        p_rows = [r for r in rows if r["policy"] == p]
        cost[p] = sum(float(r["cost_usd"]) for r in p_rows)
    savings_pct = 100.0 * (cost["FIXED_FRONTIER"] - cost["POLICY_CONSTRAINED_ROUTING"]) / cost["FIXED_FRONTIER"]
    assert 20.0 <= savings_pct <= 25.0, (
        f"Cost savings {savings_pct:.1f}% is outside the expected "
        f"[20%, 25%] range. C-011 claims 22.2%."
    )


def test_scored_routing_is_17pct_faster():
    """POLICY_CONSTRAINED_ROUTING latency must be ~17.2% lower than
    FIXED_FRONTIER latency (per C-011)."""
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_PATH)))
    lat = {}
    for p in ("FIXED_FRONTIER", "POLICY_CONSTRAINED_ROUTING"):
        p_rows = [r for r in rows if r["policy"] == p]
        lat[p] = sum(float(r["latency_ms"]) for r in p_rows) / len(p_rows)
    savings_pct = 100.0 * (lat["FIXED_FRONTIER"] - lat["POLICY_CONSTRAINED_ROUTING"]) / lat["FIXED_FRONTIER"]
    assert 15.0 <= savings_pct <= 20.0, (
        f"Latency savings {savings_pct:.1f}% is outside the expected "
        f"[15%, 20%] range. C-011 claims 17.2%."
    )


def test_no_constraint_violations():
    """All 100 runs must show 0 constraint violations (per C-011)."""
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_PATH)))
    cv = [r for r in rows if r["constraint_violation"] == "True"]
    assert not cv, (
        f"{len(cv)} constraint violations found. C-011 requires 0."
    )


def test_no_routing_failures():
    """All 100 runs must show 0 routing failures (the routing policy
    must always select an eligible provider)."""
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_PATH)))
    rf = [r for r in rows if r["routing_failure"] == "True"]
    assert not rf, (
        f"{len(rf)} routing failures found."
    )
