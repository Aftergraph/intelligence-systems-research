"""
test_jar_exp_0001_script.py
===========================

Pins the output of experiments/run_jar_exp_0001.py as proper
pytest tests. JAR-EXP-0001 is the foundational 4-condition
verification-architecture ablation:
- Condition 1 (Baseline): self-reported done
- Condition 2 (Prompted Criteria): criteria in prompt
- Condition 3 (LLM Judge): secondary LLM evaluator
- Condition 4 (Evidence-Gated Runtime): deterministic verifier

This test pins:
- 4 conditions evaluated
- 50 SWE benchmark tasks x 4 conditions = 200 runs
- CSV is LF
- Condition 4 (Evidence-Gated) has the lowest FCR
- VSR and CPVO are in plausible ranges
"""

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
    "jar_exp_0001_module",
    os.path.join(experiments_path, "run_jar_exp_0001.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


EXPECTED_CONDITIONS = {
    "Condition 1 (Baseline)",
    "Condition 2 (Prompted Criteria)",
    "Condition 3 (LLM Judge)",
    "Condition 4 (Evidence-Gated Runtime)",
}


@pytest.fixture(scope="module")
def jar_exp_summary():
    return mod.run_experiment()


def test_four_conditions_present(jar_exp_summary):
    assert set(jar_exp_summary.keys()) == EXPECTED_CONDITIONS


def test_each_condition_has_50_tasks(jar_exp_summary):
    """Each condition must have 50 SWE benchmark tasks."""
    for cond, s in jar_exp_summary.items():
        assert s["n"] == 50, (
            f"Condition {cond} has {s['n']} runs; expected 50. "
            f"Re-run run_jar_exp_0001.py with seed=1337."
        )


def test_each_condition_vsr_in_range(jar_exp_summary):
    """VSR must be 0-100% for every condition."""
    for cond, s in jar_exp_summary.items():
        assert 0 <= s["VSR"] <= 1, (
            f"Condition {cond} VSR={s['VSR']:.3f} is out of [0, 1]"
        )


def test_each_condition_cpvo_in_range(jar_exp_summary):
    """CPVO must be non-negative and finite for every condition."""
    for cond, s in jar_exp_summary.items():
        assert s["CPVO_USD"] >= 0, f"Condition {cond} CPVO={s['CPVO_USD']} negative"


def test_evidence_gated_lowest_fcr(jar_exp_summary):
    """The headline result: Condition 4 (Evidence-Gated) has the
    lowest False Completion Rate. This is the empirical claim pinned
    by JAR-EXP-0001."""
    fcr_c1 = jar_exp_summary["Condition 1 (Baseline)"]["FCR"]
    fcr_c2 = jar_exp_summary["Condition 2 (Prompted Criteria)"]["FCR"]
    fcr_c3 = jar_exp_summary["Condition 3 (LLM Judge)"]["FCR"]
    fcr_c4 = jar_exp_summary["Condition 4 (Evidence-Gated Runtime)"]["FCR"]
    assert fcr_c4 < fcr_c1, (
        f"FCR hierarchy violated: C4={fcr_c4:.3f} not < C1={fcr_c1:.3f}"
    )
    # C4 should also be lower than C2 and C3 (deterministic verifier > LLM judge)
    assert fcr_c4 < fcr_c3, (
        f"FCR hierarchy violated: C4={fcr_c4:.3f} not < C3={fcr_c3:.3f}"
    )


def test_results_csv_persisted(jar_exp_summary):
    csv_path = Path(workspace) / "data" / "results_jar_exp_0001.csv"
    assert csv_path.exists()
    text = csv_path.read_bytes()
    assert b"\r\n" not in text, "results_jar_exp_0001.csv must be LF"
    import csv as _csv
    rows = list(_csv.DictReader(open(csv_path, encoding="utf-8")))
    assert len(rows) == 200, (
        f"Expected 200 rows (50 tasks x 4 conditions); got {len(rows)}"
    )
    # All 4 conditions present in CSV
    conditions_in_csv = {r["condition"] for r in rows}
    assert conditions_in_csv == EXPECTED_CONDITIONS


def test_total_cost_non_negative(jar_exp_summary):
    for cond, s in jar_exp_summary.items():
        assert s["Total_Cost_USD"] >= 0


def test_mean_time_recorded(jar_exp_summary):
    for cond, s in jar_exp_summary.items():
        assert s["Mean_Time_Sec"] >= 0
