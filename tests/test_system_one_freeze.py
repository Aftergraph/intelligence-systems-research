import hashlib
import json
from pathlib import Path

from experiments.system_one_acceleration.protocol import ELIGIBLE_DECISION_TYPES
from experiments.system_one_acceleration.calibration_receipt import (
    calibration_corpus_sha256,
    canonical_sha256,
)
from experiments.system_one_acceleration.corpus import build_calibration_corpus

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "data" / "jar_exp_0014_question_contracts_v01.json"
WORKLOAD = ROOT / "data" / "jar_exp_0014_workload_plan_v01.json"
S11 = ROOT / "data" / "study011_workload_manifest.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_question_contracts_are_frozen_and_exactly_match_eligible_decisions():
    data = _load(QUESTIONS)
    assert data["status"] == "FROZEN_PRECALIBRATION"
    assert set(data["contracts"]) == set(ELIGIBLE_DECISION_TYPES)
    assert _sha(QUESTIONS) == "30c33ddf3dc748b90e4b52eff025540eb1e51e4e907a0551759d344674924667"


def test_question_contracts_are_typed_not_open_ended():
    data = _load(QUESTIONS)
    for key, contract in data["contracts"].items():
        assert contract["type"] in {"noul", "choice", "score"}, key
        assert contract["instructions"].strip(), key
        if contract["type"] in {"choice", "score"}:
            assert contract["criteria"], key


def test_workload_plan_reuses_only_existing_frozen_study011_inputs():
    plan = _load(WORKLOAD)
    source = _load(S11)
    assert plan["source"]["root_hash"] == source["root_hash"]
    source_ids = {row["workload_id"] for row in source["workloads"]}
    planned_ids = {
        workload_id
        for family in plan["families"]
        for workload_id in family["source_workloads"]
    }
    assert planned_ids <= source_ids
    assert plan["source"]["reuse_rule"].endswith("Do not pool or import STUDY-011 outcomes.")


def test_workload_plan_is_270_runs_and_balanced_across_three_arms():
    plan = _load(WORKLOAD)
    assert set(plan["arms"]) == {"A", "B", "C"}
    assert len(plan["families"]) == 3
    assert all(family["runs_per_arm"] == 30 for family in plan["families"])
    assert all(sum(family["replication_counts"]) == 30 for family in plan["families"])
    expected = len(plan["arms"]) * sum(f["runs_per_arm"] for f in plan["families"])
    assert expected == plan["planned_mission_runs"] == 270
    assert plan["minimum_eligible_decision_points_per_mission"] >= 3


def test_workload_plan_forbids_prior_result_pooling_and_live_execution():
    plan = _load(WORKLOAD)
    assert plan["pooling"] == {
        "study011_outcomes": False,
        "study012_outcomes": False,
        "cross_arm_pooling_before_primary_analysis": False,
    }
    assert plan["live_execution_authorized"] is False
    assert _sha(WORKLOAD) == "04d6591d94d9c074918673d078cc9b19637598c5c644318bea4bde748e569852"


def test_calibration_corpus_logical_hash_is_frozen():
    assert calibration_corpus_sha256(build_calibration_corpus()) == (
        "2b58867c78ebfff32ddc711d5987fbb8dcb3e034572966391d9291130fbec251"
    )


def test_calibration_protocol_canonical_hash_is_frozen():
    protocol = _load(ROOT / "data" / "jar_exp_0014_calibration_protocol_v01.json")
    assert canonical_sha256(protocol) == (
        "789585a4790b8467ff8d72618018e1bb74e95e2c0f6bf136a76d45de6272b89d"
    )
