import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "data" / "study012_power_plan.json"
SHA = ROOT / "data" / "study012_power_plan.json.sha256"


def load():
    return json.loads(PLAN.read_text())


def test_power_plan_is_frozen_and_integrity_bound():
    raw = PLAN.read_bytes()
    assert SHA.read_text().strip() == hashlib.sha256(raw).hexdigest()
    plan = json.loads(raw)
    assert plan["study_id"] == "STUDY-012"
    assert plan["experiment_id"] == "ICT-EXP-001"
    assert plan["gate"] == "G12-8"
    assert plan["freeze_version"] == "v1.0.0"
    assert plan["outcome_blind"] is True
    assert plan["observed_outcomes_used"] is False
    assert plan["confirmatory_execution_authorized"] is False


def test_power_parameters_and_required_sample_are_recomputable():
    from scripts.study012_power_analysis import conservative_two_proportion_n
    p = load()["planning_parameters"]
    assert p == {"alpha_two_sided": 0.01, "power": 0.80, "baseline_rate": 0.50, "minimum_material_difference": 0.10}
    assert conservative_two_proportion_n(**p) == 577
    assert load()["required_observations_per_condition"] == 577


def test_run_math_uses_current_six_primary_pairs_not_old_draft_shape():
    plan = load()
    assert plan["primary_pair_count"] == 6
    assert plan["replicates_required"] == 97
    assert plan["achieved_observations_per_condition"] == 582
    assert plan["primary_i5_i6_runs"] == 1164
    assert plan["full_i0_i6_ladder_runs"] == 4074


def test_plan_explicitly_treats_independent_formula_as_conservative_bound_for_paired_design():
    plan = load()
    assert plan["design"] == "PAIRED_I6_VS_I5"
    assert plan["planning_method"] == "CONSERVATIVE_INDEPENDENT_TWO_PROPORTION_UPPER_BOUND"
    assert "discordance" in plan["paired_design_note"].lower()
    assert plan["empirical_conclusions"] == []
