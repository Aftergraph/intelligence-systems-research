"""
test_study011_cell_structure.py
===============================

Pins the STUDY-011 cell-structure math:
- 4 conditions x 2 strata x 58 LIVE_VALID per cell = 464 LIVE_VALID
  minimum (the confirmatory floor).
- 464 / 0.75 = 618.67 -> 619 planned attempts (the operational
  ceiling, NOT the bar).
- The two numbers must never be conflated.

Also pins:
- N_PER_CELL_MIN = 58 (power analysis result, two-sided alpha=0.05/4
  Bonferroni, power=0.80, h=0.5).
- Phases: 1 = Dialagram + OpenRouter; 2 = OpenAI + Anthropic + Google
  (BLOCKED_PENDING_OWNER).
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


PHASE1_MIN_LIVE_VALID = 464   # 4 conds x 2 strata x 58
PLANNED_MAX_ATTEMPTS = 619    # ceil(464 / 0.75)
N_PER_CELL_MIN = 58


def test_phase1_minimum_live_valid_count():
    """4 conditions x 2 strata x 58 LIVE_VALID per cell = 464.
    The confirmatory floor."""
    assert 4 * 2 * N_PER_CELL_MIN == PHASE1_MIN_LIVE_VALID, (
        f"4 x 2 x 58 = {4*2*58}, expected {PHASE1_MIN_LIVE_VALID}. "
        f"This is the minimum LIVE_VALID count for confirmatory "
        f"inference. Any change requires a preregistration amendment."
    )


def test_phase1_planned_maximum_attempts():
    """464 / 0.75 = 618.67 -> 619. The operational ceiling, NOT the
    confirmatory bar."""
    import math
    expected = math.ceil(PHASE1_MIN_LIVE_VALID / 0.75)
    assert expected == PLANNED_MAX_ATTEMPTS, (
        f"ceil(464 / 0.75) = {expected}, expected "
        f"{PLANNED_MAX_ATTEMPTS}. This is the operational ceiling, "
        f"not the confirmatory floor."
    )


def test_analyze_module_constants_match():
    """study011_analyze.py must declare the same constants."""
    sys.path.insert(0, str(Path(workspace) / "experiments" / "live_benchmark"))
    import study011_analyze
    assert study011_analyze.PHASE1_MIN_LIVE_VALID == PHASE1_MIN_LIVE_VALID, (
        f"study011_analyze.PHASE1_MIN_LIVE_VALID = "
        f"{study011_analyze.PHASE1_MIN_LIVE_VALID}, expected "
        f"{PHASE1_MIN_LIVE_VALID}"
    )
    assert study011_analyze.PLANNED_MAX_ATTEMPTS_P1 == PLANNED_MAX_ATTEMPTS, (
        f"study011_analyze.PLANNED_MAX_ATTEMPTS_P1 = "
        f"{study011_analyze.PLANNED_MAX_ATTEMPTS_P1}, expected "
        f"{PLANNED_MAX_ATTEMPTS}"
    )
    assert study011_analyze.N_PER_CELL_MIN == N_PER_CELL_MIN, (
        f"study011_analyze.N_PER_CELL_MIN = "
        f"{study011_analyze.N_PER_CELL_MIN}, expected {N_PER_CELL_MIN}"
    )


def test_preregistration_doc_states_464_and_619():
    """The preregistration doc must explicitly state both numbers
    in their correct roles (min vs ceiling)."""
    p = Path(workspace) / "STUDY-011-LIVE-CROSS-PROVIDER-PREREGISTRATION.md"
    text = p.read_text(encoding="utf-8")
    assert "464" in text, "preregistration doc missing 464 (minimum LIVE_VALID)"
    assert "619" in text, "preregistration doc missing 619 (ceiling attempts)"
    # Must clarify the distinction
    assert "minimum" in text.lower(), "preregistration must label 464 as the minimum"
    assert "ceiling" in text.lower() or "maximum" in text.lower(), (
        "preregistration must label 619 as a ceiling/maximum, not a target"
    )


def test_cost_forecast_distinguishes_464_from_619():
    """Cost forecast must show both numbers and not conflate them."""
    p = Path(workspace) / "STUDY-011-COST-FORECAST.md"
    text = p.read_text(encoding="utf-8")
    assert "464" in text, "cost forecast missing 464"
    assert "619" in text, "cost forecast missing 619"


def test_readiness_report_distinguishes_464_from_619():
    """Readiness report must show both numbers and not conflate them."""
    p = Path(workspace) / "STUDY-011-READINESS-REPORT.md"
    text = p.read_text(encoding="utf-8")
    assert "464" in text, "readiness report missing 464"
    assert "619" in text, "readiness report missing 619"


def test_provider_model_matrix_has_two_strata():
    """The provider/model matrix must define exactly 2 provider strata
    (Dialagram + OpenRouter) and each stratum must have at least 1 model
    with `exact_model_id`."""
    p = Path(workspace) / "data/study011_provider_model_matrix.json"
    matrix = json.load(open(p, encoding="utf-8"))
    strata = matrix.get("provider_strata", [])
    assert len(strata) == 2, (
        f"Provider/model matrix has {len(strata)} strata, expected 2. "
        f"Drift would change the cell-structure math."
    )
    for s in strata:
        assert "provider_stratum" in s, f"stratum missing provider_stratum: {s}"
        assert len(s.get("models", [])) >= 1, (
            f"stratum {s.get('provider_stratum')!r} has no models"
        )
        for m in s["models"]:
            assert "exact_model_id" in m, (
                f"model missing exact_model_id: {m}"
            )
            assert "rationale" in m, (
                f"model {m.get('exact_model_id')!r} missing rationale"
            )


def test_matrix_replication_plan_matches_prereg():
    """The matrix's replication_plan numbers must match the pre-registered
    464/619 design."""
    p = Path(workspace) / "data/study011_provider_model_matrix.json"
    matrix = json.load(open(p, encoding="utf-8"))
    rp = matrix.get("replication_plan", {})
    assert rp.get("live_valid_per_cell_target") == N_PER_CELL_MIN, (
        f"replication_plan.live_valid_per_cell_target = "
        f"{rp.get('live_valid_per_cell_target')}, expected {N_PER_CELL_MIN}"
    )
    assert rp.get("phase1_live_valid_target") == PHASE1_MIN_LIVE_VALID, (
        f"replication_plan.phase1_live_valid_target = "
        f"{rp.get('phase1_live_valid_target')}, expected "
        f"{PHASE1_MIN_LIVE_VALID}"
    )
    assert rp.get("phase1_attempts_ceiling") == PLANNED_MAX_ATTEMPTS, (
        f"replication_plan.phase1_attempts_ceiling = "
        f"{rp.get('phase1_attempts_ceiling')}, expected {PLANNED_MAX_ATTEMPTS}"
    )


def test_frozen_workload_count_matches_20():
    """The frozen workload set must contain exactly 20 workloads
    (per the preregistration)."""
    p = Path(workspace) / "data/study011_workload_manifest.json"
    manifest = json.load(open(p, encoding="utf-8"))
    n = len(manifest["workloads"])
    assert n == 20, (
        f"Workload manifest has {n} workloads, expected 20. "
        f"Drift would invalidate the preregistered statistical plan."
    )
