"""
test_statistical_audit.py
==========================

Pins the math primitives in experiments/statistical_audit.py
(Wilson score interval and Cohen's h effect size) and the audit
output against three datasets (JAR-EXP-0001, MISSION-Bench, Confounder).

ponytail: pinning the math is the lowest-hanging fruit. The CI
calculation is the *primary* defense against the "elimination"
overclaim — getting the math wrong would invalidate the audit.
"""

import importlib.util
import math
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
    "statistical_audit_module",
    os.path.join(experiments_path, "statistical_audit.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


# ============================================================================
# Wilson score interval
# ============================================================================

def test_wilson_zero_total():
    """Total=0 must return (0.0, 0.0) — no information, no spread."""
    lower, upper = mod.wilson_score_interval(0, 0)
    assert lower == 0.0
    assert upper == 0.0


def test_wilson_known_case_p50_n100():
    """50/100 = 50%, 95% Wilson CI: should be approximately [40.3%, 59.7%]
    (the classic 50% binomial). Allow some tolerance.
    Reference: standard Wilson CI table."""
    lower, upper = mod.wilson_score_interval(50, 100)
    assert 39 <= lower <= 42, f"Lower {lower} not in expected range"
    assert 58 <= upper <= 61, f"Upper {upper} not in expected range"


def test_wilson_zero_successes():
    """0/N should give a CI that is bounded away from 0 (Wilson is
    well-behaved at the boundary; normal approximation would give
    CI [-something, something])."""
    lower, upper = mod.wilson_score_interval(0, 100)
    assert 0 <= lower <= 2
    assert 0 <= upper <= 5
    assert lower <= upper


def test_wilson_all_successes():
    """N/N should give a CI that is bounded below 1 (i.e. upper = 100,
    lower bounded)."""
    lower, upper = mod.wilson_score_interval(100, 100)
    assert lower >= 95, f"Lower {lower} should be close to 100"
    assert upper == 100.0


def test_wilson_monotonic_in_n():
    """As N grows, the CI width must shrink (more data = more certainty)."""
    lo_50, hi_50 = mod.wilson_score_interval(5, 50)
    lo_500, hi_500 = mod.wilson_score_interval(50, 500)
    width_50 = hi_50 - lo_50
    width_500 = hi_500 - lo_500
    assert width_500 < width_50, (
        f"Width at N=500 ({width_500}) not < width at N=50 ({width_50}). "
        f"Wilson CI must shrink with N."
    )


# ============================================================================
# Cohen's h
# ============================================================================

def test_cohens_h_zero_for_equal_proportions():
    """Cohen's h must be 0 when p1 == p2 (no effect)."""
    h = mod.cohens_h(0.5, 0.5)
    assert h == 0.0


def test_cohens_h_positive_for_unequal():
    """Cohen's h must be > 0 when p1 != p2."""
    h = mod.cohens_h(0.9, 0.1)
    assert h > 0, f"Cohen's h = {h}; expected > 0"


def test_cohens_h_symmetric():
    """Cohen's h must be symmetric: |p1-p2| = |p2-p1|."""
    h1 = mod.cohens_h(0.9, 0.1)
    h2 = mod.cohens_h(0.1, 0.9)
    assert h1 == h2


def test_cohens_h_known_value():
    """Cohen's h between 0.5 and 0.7 should be approximately:
    h = 2*asin(sqrt(0.5)) - 2*asin(sqrt(0.7))
    = 2*0.7854 - 2*0.9912
    = 1.5708 - 1.9824
    = -0.4116
    |h| = 0.412
    """
    expected = abs(2 * math.asin(math.sqrt(0.5)) - 2 * math.asin(math.sqrt(0.7)))
    h = mod.cohens_h(0.5, 0.7)
    assert abs(h - round(expected, 3)) < 0.005, (
        f"Cohen's h = {h}; expected ~{round(expected, 3)}"
    )


def test_cohens_h_clamps_proportions():
    """Cohen's h must clamp p1, p2 to [0, 1] to avoid math domain errors."""
    h_below = mod.cohens_h(-0.1, 0.5)
    h_above = mod.cohens_h(1.5, 0.5)
    # Both should be valid (not raise) and non-negative.
    assert h_below >= 0
    assert h_above >= 0


# ============================================================================
# audit_datasets integration
# ============================================================================

@pytest.fixture(scope="module")
def audit_records():
    return mod.audit_datasets()


def test_audit_includes_jar_exp_0001(audit_records):
    datasets = {r["dataset"] for r in audit_records}
    assert any("JAR-EXP-0001" in d for d in datasets), (
        f"Audit missing JAR-EXP-0001. Datasets: {datasets}"
    )


def test_audit_includes_mission_bench(audit_records):
    datasets = {r["dataset"] for r in audit_records}
    assert any("MISSION-Bench" in d for d in datasets), (
        f"Audit missing MISSION-Bench. Datasets: {datasets}"
    )


def test_audit_includes_confounder(audit_records):
    datasets = {r["dataset"] for r in audit_records}
    assert any("Confounder" in d for d in datasets), (
        f"Audit missing Confounder. Datasets: {datasets}"
    )


def test_audit_records_have_required_fields(audit_records):
    required = {
        "dataset", "condition", "sample_size", "declared_successes",
        "actual_verified", "false_completions", "VSR_pct", "VSR_95_CI",
        "FCR_pct", "FCR_95_CI",
    }
    for r in audit_records:
        missing = required - set(r.keys())
        assert not missing, f"Record missing fields: {missing}"


def test_audit_ci_format_is_brackets(audit_records):
    """Each CI field must be of the form '[lower%, upper%]'."""
    for r in audit_records:
        for field in ("VSR_95_CI", "FCR_95_CI"):
            v = r[field]
            assert v.startswith("["), f"CI {field}={v} doesn't start with ["
            assert v.endswith("]"), f"CI {field}={v} doesn't end with ]"
            assert "%" in v, f"CI {field}={v} doesn't have %"


def test_audit_sample_size_positive(audit_records):
    for r in audit_records:
        assert r["sample_size"] > 0, (
            f"Dataset {r['dataset']} condition {r['condition']} has N=0"
        )


def test_audit_csv_persisted_lf(audit_records):
    csv_path = Path(workspace) / "data" / "statistical_audit_recomputed.csv"
    assert csv_path.exists()
    text = csv_path.read_bytes()
    assert b"\r\n" not in text, "statistical_audit_recomputed.csv must be LF"
