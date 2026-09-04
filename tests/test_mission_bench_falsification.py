"""
test_mission_bench_falsification.py
===================================

Pins the MISSION-Bench ablation ladder results. The bench has 8 stages
(1_baseline through 8_full_system) and FCR drops from 61% to 0% only
when verification is added (stage 5+).

This test is the most important regression test in the program:
it pins the FCR reduction pattern that the entire C-001 claim depends
on. If the FCR in stages 5+ ever reverts to non-zero, C-001 is broken.

It also catches front-door overclaims: the claim is "FCR = 0.0% in
MISSION-Bench (N=800)" but that's only true for the 4 verification-
enabled stages (5/6/7/8) totaling 400 runs. The other 400 runs (stages
1-4) have FCR between 36% and 61%.
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


RESULTS_CSV = "data/results_mission_bench.csv"
EXPECTED_STAGES = {
    "1_baseline", "2_plus_mission", "3_plus_state", "4_plus_authority",
    "5_plus_verification", "6_plus_evidence", "7_plus_recovery",
    "8_full_system",
}
VERIFICATION_ON_STAGES = {
    "5_plus_verification", "6_plus_evidence", "7_plus_recovery",
    "8_full_system",
}
# These stages have verification enabled and FCR should be 0
ZERO_FCR_STAGES = VERIFICATION_ON_STAGES


def test_results_csv_exists():
    p = Path(workspace) / RESULTS_CSV
    assert p.exists(), f"{RESULTS_CSV} missing"
    assert p.stat().st_size > 0, f"{RESULTS_CSV} is empty"


def test_results_csv_has_8_stages():
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_CSV)))
    stages = {r["ablation_stage"] for r in rows}
    assert stages == EXPECTED_STAGES, (
        f"Stages {stages} != expected {EXPECTED_STAGES}. "
        f"A new stage was added or a stage was renamed."
    )


def test_results_csv_has_100_runs_per_stage():
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_CSV)))
    by_stage = {}
    for r in rows:
        by_stage.setdefault(r["ablation_stage"], 0)
        by_stage[r["ablation_stage"]] += 1
    for s in EXPECTED_STAGES:
        n = by_stage.get(s, 0)
        assert n == 100, (
            f"Stage {s} has {n} runs, expected 100. "
            f"Per-stage sample size drift would break the power analysis."
        )


def test_verification_stages_have_zero_fcr():
    """Stages 5-8 (verification enabled) must show FCR = 0%."""
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_CSV)))
    for stage in ZERO_FCR_STAGES:
        stage_rows = [r for r in rows if r["ablation_stage"] == stage]
        fcr_count = sum(
            1 for r in stage_rows if r["is_false_completion"] == "True"
        )
        assert fcr_count == 0, (
            f"Stage {stage} has {fcr_count} false completions. "
            f"Stage 5+ must show FCR=0 to support claim C-001. "
            f"This is a major regression."
        )


def test_baseline_fcr_is_high():
    """The baseline stage must show FCR > 30% (otherwise the
    verification impact is unmeasurable)."""
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_CSV)))
    baseline = [r for r in rows if r["ablation_stage"] == "1_baseline"]
    fcr_count = sum(1 for r in baseline if r["is_false_completion"] == "True")
    pct = 100.0 * fcr_count / len(baseline)
    assert pct > 30.0, (
        f"Baseline FCR is {pct:.1f}%, expected > 30%. "
        f"Without a high baseline, the C-001 reduction is unmeasurable."
    )


def test_fcr_monotonically_decreases_or_equals_through_stages():
    """FCR should not increase as more components are added (the
    ablation ladder demonstrates a monotone improvement)."""
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_CSV)))
    by_stage = {}
    for r in rows:
        s = r["ablation_stage"]
        if s not in by_stage:
            by_stage[s] = {"n": 0, "fcr": 0}
        by_stage[s]["n"] += 1
        if r["is_false_completion"] == "True":
            by_stage[s]["fcr"] += 1
    # Stages in order
    order = [
        "1_baseline", "2_plus_mission", "3_plus_state",
        "4_plus_authority", "5_plus_verification", "6_plus_evidence",
        "7_plus_recovery", "8_full_system",
    ]
    rates = [
        100.0 * by_stage[s]["fcr"] / by_stage[s]["n"] for s in order
    ]
    # Monotone non-increase (allow equal but not increase)
    for i in range(len(rates) - 1):
        assert rates[i] >= rates[i + 1], (
            f"FCR increases from stage {order[i]} ({rates[i]:.1f}%) to "
            f"stage {order[i+1]} ({rates[i+1]:.1f}%). The ablation ladder "
            f"must show monotone non-increasing FCR."
        )


def test_frontdoor_precise_about_fcr_coverage():
    """The front-door docs must NOT say "FCR = 0.0% in N=800" without
    qualification. The 0% applies to stages 5-8 (400 runs), not all
    800. If the docs claim FCR=0% over the full 800, that's an
    overclaim."""
    import re
    # Look for the FCR row in the table
    fcr_pattern = re.compile(
        r"False Completion Rate.*?0\.0%.*?(?=\n)", re.DOTALL
    )
    n_mention_pattern = re.compile(r"N[=:\s]+(\d+)")
    for doc in ["README.md", "00-EXECUTIVE-SUMMARY.md"]:
        text = (Path(workspace) / doc).read_text(encoding="utf-8")
        # Find the FCR row
        for line in text.splitlines():
            if "False Completion Rate" in line and "0.0%" in line:
                # Check that N is qualified or that the 0% is qualified
                # Allowed: "0.0% in N=100", "0.0% in MISSION-Bench"
                # Disallowed: "0.0% in N=800" (because N=800 includes stages 1-4)
                m = n_mention_pattern.search(line)
                if m and int(m.group(1)) == 800:
                    # If N=800 is mentioned with 0.0% in the same line,
                    # the front-door is overclaiming.
                    pytest.fail(
                        f"{doc} FCR row says '0.0% in N=800' but the "
                        f"0% FCR is only true for stages 5-8 (N=400). "
                        f"Stage 1-4 have FCR between 36% and 61%. "
                        f"Update the front-door to qualify the claim."
                    )
