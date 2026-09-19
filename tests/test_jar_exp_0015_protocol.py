import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "data" / "jar_exp_0015_protocol_v01.json"


def test_jar_exp_0015_protocol_is_prospective_and_frozen():
    p = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert p["schema_version"] == "jar-exp-0015.protocol/0.1"
    assert p["experiment_id"] == "JAR-EXP-0015"
    assert p["parent_experiment_id"] == "JAR-EXP-0014"
    assert p["status"] == "FROZEN_PREEXECUTION"
    assert p["network_calls_authorized"] is False
    assert p["parent_data_role"] == "DIAGNOSTIC_DESIGN_ONLY_NOT_ADMISSIBLE_AS_0015_OBSERVATIONS"


def test_dataset_math_and_holdout_separation():
    p = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    d = p["dataset"]
    assert len(d["decision_types"]) == 8
    assert d["cases_per_decision_type"] == 40
    assert d["calibration_per_decision_type"] == 24
    assert d["holdout_per_decision_type"] == 16
    assert d["total_cases"] == 8 * 40
    assert 24 + 16 == 40
    assert d["split_frozen_before_inference"] is True
    assert d["exact_parent_case_duplicates_forbidden"] is True


def test_threshold_and_promotion_rules_fail_closed():
    p = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    t = p["threshold_rule"]
    assert t["minimum_accepted_coverage"] == 0.30
    assert t["maximum_wilson_upper_error"] == 0.05
    assert t["maximum_critical_accepted_errors"] == 0
    assert t["no_feasible_threshold"] == "NO_THRESHOLD"
    promotion = p["promotion"]
    assert promotion["requires_frozen_policy_before_holdout"] is True
    assert promotion["critical_holdout_errors_max"] == 0
    assert promotion["fallback_required_for_infeasible_classes"] is True
    assert promotion["failure_outcome"] == "NO_PROMOTION"


def test_authority_boundary_is_advisory_only():
    p = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    a = p["authority_boundary"]
    assert a == {
        "system_one_role": "ADVISORY_ONLY",
        "grants_authority": False,
        "grants_verification": False,
        "grants_execution_truth": False,
    }


def test_contract_revision_scope_is_not_posthoc_unbounded():
    p = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert set(p["initially_revision_eligible"]) == {
        "risk_level",
        "route_model",
        "result_sufficient",
    }


def test_protocol_binds_frozen_dataset_and_parent_evidence():
    p = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    d = p["dataset"]
    assert d["dataset_ref"] == "data/jar_exp_0015_dataset_v01.json"
    assert d["dataset_sha256"] == "de90286586397af21a568a91c4cd4ec4d56ccfd8a7db09fbd2d7167f6541fac9"
    assert d["split_manifest_ref"] == "data/jar_exp_0015_split_manifest_v01.json"
    assert d["split_manifest_sha256"] == "185f5ca9ed25286fb3c60092f83357e0493038338b08bbdd9b4251c9f01707d1"
    assert d["parent_terminal_head"] == "204aaf78e05250add39a6e91f9c23dd545109a1a"
    assert d["parent_observations_sha256"] == "4e97753205e2c5bfd731ab65773cddf8d40af2604656e9a3fa163a82d3f18955"
