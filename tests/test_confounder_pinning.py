"""
test_confounder_pinning.py
===========================

Pins the STUDY-005 confounder analysis. The claim C-007 is:
"Evidence gating is the causal prerequisite that enables retry loops
to work. McNemar p < 0.0001, VSR +29.0% [18.2%, 39.1%]."

This test pins:
- 4 conditions (A=Baseline 1-shot, B=Baseline + 3 retries,
  C=Evidence-Gated 1-shot, D=Evidence-Gated + 3 retries)
- 100 tasks per condition (N=400 total)
- FCR is 0 in Conditions C and D (the evidence-gated ones)
- FCR is non-zero in Conditions A and B (the non-gated ones)
- The McNemar statistic is computable from the raw data
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


RESULTS_PATH = "data/results_confounder_analysis.csv"
EXPECTED_CONDITIONS = {
    "Condition A (Baseline 1-shot)",
    "Condition B (Baseline + 3 Retries)",
    "Condition C (Evidence-Gated 1-shot)",
    "Condition D (Evidence-Gated + 3 Retries)",
}
EXPECTED_TASKS_PER_CONDITION = 100


def test_results_csv_exists():
    p = Path(workspace) / RESULTS_PATH
    assert p.exists(), f"{RESULTS_PATH} missing"


def test_results_has_4_conditions():
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_PATH)))
    conds = {r["condition"] for r in rows}
    assert conds == EXPECTED_CONDITIONS, (
        f"Conditions {conds} != expected {EXPECTED_CONDITIONS}. "
        f"A condition was added or renamed; this is a protocol change."
    )


def test_results_has_100_per_condition():
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_PATH)))
    by_cond = {}
    for r in rows:
        by_cond.setdefault(r["condition"], 0)
        by_cond[r["condition"]] += 1
    for c in EXPECTED_CONDITIONS:
        n = by_cond.get(c, 0)
        assert n == EXPECTED_TASKS_PER_CONDITION, (
            f"Condition {c} has {n} tasks, expected "
            f"{EXPECTED_TASKS_PER_CONDITION}."
        )


def test_evidence_gated_conditions_have_zero_fcr():
    """Conditions C and D (evidence-gated) must show FCR = 0%."""
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_PATH)))
    for cond in ("Condition C (Evidence-Gated 1-shot)",
                 "Condition D (Evidence-Gated + 3 Retries)"):
        c_rows = [r for r in rows if r["condition"] == cond]
        fcr = sum(1 for r in c_rows if r["is_false_completion"] == "True")
        assert fcr == 0, (
            f"{cond} has {fcr} false completions. "
            f"Evidence gating is the prerequisite for C-007; if any FCR "
            f"re-appears, the claim is broken."
        )


def test_baseline_conditions_have_nonzero_fcr():
    """Conditions A and B (no evidence gating) must have FCR > 0.
    Otherwise the confounder analysis is unmeasurable."""
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_PATH)))
    for cond in ("Condition A (Baseline 1-shot)",
                 "Condition B (Baseline + 3 Retries)"):
        c_rows = [r for r in rows if r["condition"] == cond]
        fcr = sum(1 for r in c_rows if r["is_false_completion"] == "True")
        assert fcr > 0, (
            f"{cond} has 0 false completions. Without baseline FCR, "
            f"the confounder effect is unmeasurable."
        )


def test_vsr_increases_with_evidence_gating():
    """VSR must be higher in evidence-gated conditions (C, D) than
    in baseline conditions (A, B). The 2x2 design: A < B (retries help
    a little), A < C (gating helps a lot), A < D (both help most)."""
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_PATH)))
    vsr = {}
    for c in EXPECTED_CONDITIONS:
        c_rows = [r for r in rows if r["condition"] == c]
        vsr[c] = sum(
            1 for r in c_rows
            if r["actual_success"] == "True" and r["is_verified"] == "True"
        )
    # Critical ordering
    assert vsr["Condition A (Baseline 1-shot)"] < vsr["Condition C (Evidence-Gated 1-shot)"], (
        f"VSR(A)={vsr['Condition A (Baseline 1-shot)']} not < "
        f"VSR(C)={vsr['Condition C (Evidence-Gated 1-shot)']}. "
        f"Evidence gating alone should raise VSR."
    )
    assert vsr["Condition B (Baseline + 3 Retries)"] < vsr["Condition D (Evidence-Gated + 3 Retries)"], (
        f"VSR(B)={vsr['Condition B (Baseline + 3 Retries)']} not < "
        f"VSR(D)={vsr['Condition D (Evidence-Gated + 3 Retries)']}. "
        f"Evidence gating + retries should raise VSR more than retries alone."
    )


def test_paired_task_design():
    """The 2x2 design is between-subjects on the same 100 tasks.
    Every task_id in Condition A must appear in C, D, and B."""
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_PATH)))
    by_cond = {}
    for r in rows:
        by_cond.setdefault(r["condition"], set()).add(r["task_id"])
    a = by_cond["Condition A (Baseline 1-shot)"]
    for c in ("Condition B (Baseline + 3 Retries)",
              "Condition C (Evidence-Gated 1-shot)",
              "Condition D (Evidence-Gated + 3 Retries)"):
        assert a == by_cond[c], (
            f"Task set in {c} differs from Condition A. "
            f"The 2x2 confounder design requires paired tasks."
        )


def test_mcnemar_b_vs_d_is_computable():
    """The B vs D comparison (retries without gating vs retries with
    gating) is the McNemar test from C-007. Verify the data supports
    the comparison (each task has both a B and a D row)."""
    rows = list(csv.DictReader(open(Path(workspace) / RESULTS_PATH)))
    by_task = {}
    for r in rows:
        by_task.setdefault(r["task_id"], {})[r["condition"]] = r
    n_paired = sum(
        1 for t, cs in by_task.items()
        if "Condition B (Baseline + 3 Retries)" in cs
        and "Condition D (Evidence-Gated + 3 Retries)" in cs
    )
    assert n_paired == 100, (
        f"Only {n_paired} tasks have both B and D rows; expected 100. "
        f"The McNemar test from C-007 requires paired data."
    )
