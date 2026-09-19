from pathlib import Path
import json
import shutil

from experiments.system_one_acceleration.preflight import evaluate_preflight
from experiments.system_one_acceleration.calibration_receipt import (
    calibration_corpus_sha256,
    canonical_sha256,
)
from experiments.system_one_acceleration.corpus import build_calibration_corpus
from experiments.system_one_acceleration.integrity import execution_manifest_sha256

ROOT = Path(__file__).resolve().parents[1]


def test_current_repository_preflight_is_fail_closed_without_network():
    result = evaluate_preflight(ROOT)
    assert result.decision == "NO_GO"
    assert set(result.blockers) == {
        "typesafe_model_not_pinned",
        "control_model_not_pinned",
        "cascade_threshold_not_frozen",
        "calibration_not_recorded",
        "execution_approval_not_recorded",
        "network_calls_not_authorized",
        "confirmatory_execution_not_authorized",
        "cost_ceiling_not_frozen",
        "provider_call_ceiling_not_frozen",
        "execution_manifest_not_frozen",
    }


def _seed_execution_manifest_code(root: Path) -> None:
    module_src = ROOT / "experiments" / "system_one_acceleration"
    module_dst = root / "experiments" / "system_one_acceleration"
    shutil.copytree(module_src, module_dst, dirs_exist_ok=True)
    (root / "schemas").mkdir(parents=True, exist_ok=True)
    for name in (
        "system-one-calibration-receipt.v0.1.json",
        "system-one-decision-receipt.v0.1.json",
        "system-one-execution-approval-receipt.v0.1.json",
    ):
        shutil.copyfile(ROOT / "schemas" / name, root / "schemas" / name)
    shutil.copyfile(ROOT / "requirements-typesafe.txt", root / "requirements-typesafe.txt")


def test_ready_requires_every_gate_to_be_explicit(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    for rel in (
        "jar_exp_0014_question_contracts_v01.json",
        "jar_exp_0014_workload_plan_v01.json",
        "jar_exp_0014_critical_risk_pack_v01.json",
        "jar_exp_0014_randomization_v01.json",
    ):
        (data / rel).write_text(
            json.dumps({"status": "FROZEN_PRECALIBRATION"}),
            encoding="utf-8",
        )

    protocol = {"status": "FROZEN_PRECALIBRATION", "rule": "fixed"}
    (data / "jar_exp_0014_calibration_protocol_v01.json").write_text(
        json.dumps(protocol), encoding="utf-8"
    )
    calibration = {
        "schema_version": "aftergraph.system-one-calibration/0.1",
        "experiment_id": "JAR-EXP-0014",
        "requested_model": "jev-latest",
        "returned_model": "jev-test-pin",
        "corpus_sha256": calibration_corpus_sha256(build_calibration_corpus()),
        "protocol_sha256": canonical_sha256(protocol),
        "result": {
            "threshold": 0.9,
            "feasible": True,
            "critical_errors": 0,
            "total": 158,
            "critical_cases": 30,
        },
        "usage": {"provider_calls": 158, "input_tokens": 1000, "output_tokens": 200},
    }
    (data / "calibration.json").write_text(json.dumps(calibration), encoding="utf-8")
    _seed_execution_manifest_code(tmp_path)
    manifest = execution_manifest_sha256(tmp_path)
    (data / "approval.json").write_text(
        json.dumps({
            "schema_version": "aftergraph.system-one-execution-approval/0.1",
            "experiment_id": "JAR-EXP-0014",
            "approved": True,
            "network_calls_authorized": True,
            "confirmatory_execution_authorized": True,
            "returned_typesafe_model_pin": "jev-test-pin",
            "control_model_pin": "control-test-pin",
            "cascade_confidence_threshold": 0.9,
            "execution_manifest_sha256": manifest,
            "max_cost_usd": 5.0,
            "max_provider_calls": 5000,
            "approved_by": "test-owner",
            "approved_at": "2026-09-19T00:00:00Z",
        }),
        encoding="utf-8",
    )

    gate = {
        "requested_typesafe_model": "jev-latest",
        "returned_typesafe_model_pin": "jev-test-pin",
        "control_model_pin": "control-test-pin",
        "cascade_confidence_threshold": 0.9,
        "calibration_receipt_ref": "data/calibration.json",
        "execution_approval_ref": "data/approval.json",
        "network_calls_authorized": True,
        "confirmatory_execution_authorized": True,
        "execution_manifest_sha256": manifest,
        "max_cost_usd": 5.0,
        "max_provider_calls": 5000,
    }
    (data / "jar_exp_0014_execution_gate_v01.json").write_text(
        json.dumps(gate),
        encoding="utf-8",
    )

    result = evaluate_preflight(tmp_path)
    assert result.decision == "READY_TO_EXECUTE"
    assert result.blockers == ()


def test_missing_frozen_input_blocks_even_if_execution_gate_is_present(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    source_gate = ROOT / "data" / "jar_exp_0014_execution_gate_v01.json"
    shutil.copyfile(source_gate, data / source_gate.name)
    result = evaluate_preflight(tmp_path)
    assert result.decision == "NO_GO"
    assert any(blocker.startswith("missing:data/") for blocker in result.blockers)


def test_stale_or_missing_calibration_evidence_blocks_ready(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    for rel in (
        "jar_exp_0014_question_contracts_v01.json",
        "jar_exp_0014_workload_plan_v01.json",
        "jar_exp_0014_critical_risk_pack_v01.json",
        "jar_exp_0014_randomization_v01.json",
    ):
        (data / rel).write_text(
            json.dumps({"status": "FROZEN_PRECALIBRATION"}), encoding="utf-8"
        )

    (data / "calibration.json").write_text(
        json.dumps({
            "schema_version": "aftergraph.system-one-calibration/0.1",
            "experiment_id": "JAR-EXP-0014",
            "returned_model": "different-model",
            "result": {
                "threshold": 0.8,
                "feasible": False,
                "critical_errors": 1,
                "total": 100,
                "critical_cases": 12,
            },
        }),
        encoding="utf-8",
    )

    gate = {
        "returned_typesafe_model_pin": "jev-test-pin",
        "control_model_pin": "control-test-pin",
        "cascade_confidence_threshold": 0.9,
        "calibration_receipt_ref": "data/calibration.json",
        "execution_approval_ref": "data/missing-approval.json",
        "network_calls_authorized": True,
        "confirmatory_execution_authorized": True,
        "max_cost_usd": 5.0,
        "max_provider_calls": 5000,
    }
    (data / "jar_exp_0014_execution_gate_v01.json").write_text(
        json.dumps(gate), encoding="utf-8"
    )

    result = evaluate_preflight(tmp_path)
    assert result.decision == "NO_GO"
    assert {
        "calibration_model_pin_mismatch",
        "calibration_threshold_mismatch",
        "calibration_not_feasible",
        "calibration_critical_error",
        "calibration_sample_too_small",
        "calibration_critical_pack_incomplete",
        "execution_approval_missing",
    }.issubset(set(result.blockers))


def test_execution_approval_must_match_frozen_execution_scope(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    for rel in (
        "jar_exp_0014_question_contracts_v01.json",
        "jar_exp_0014_workload_plan_v01.json",
        "jar_exp_0014_critical_risk_pack_v01.json",
        "jar_exp_0014_randomization_v01.json",
    ):
        (data / rel).write_text(
            json.dumps({"status": "FROZEN_PRECALIBRATION"}), encoding="utf-8"
        )
    (data / "calibration.json").write_text(
        json.dumps({
            "schema_version": "aftergraph.system-one-calibration/0.1",
            "experiment_id": "JAR-EXP-0014",
            "returned_model": "jev-test-pin",
            "result": {
                "threshold": 0.9,
                "feasible": True,
                "critical_errors": 0,
                "total": 158,
                "critical_cases": 30,
            },
        }),
        encoding="utf-8",
    )
    (data / "approval.json").write_text(
        json.dumps({
            "schema_version": "aftergraph.system-one-execution-approval/0.1",
            "experiment_id": "JAR-EXP-0014",
            "approved": True,
            "network_calls_authorized": True,
            "confirmatory_execution_authorized": True,
            "returned_typesafe_model_pin": "wrong-model",
            "control_model_pin": "control-test-pin",
            "cascade_confidence_threshold": 0.8,
            "max_cost_usd": 50.0,
            "max_provider_calls": 50000,
            "approved_by": "test-owner",
            "approved_at": "2026-09-19T00:00:00Z",
        }),
        encoding="utf-8",
    )
    gate = {
        "returned_typesafe_model_pin": "jev-test-pin",
        "control_model_pin": "control-test-pin",
        "cascade_confidence_threshold": 0.9,
        "calibration_receipt_ref": "data/calibration.json",
        "execution_approval_ref": "data/approval.json",
        "network_calls_authorized": True,
        "confirmatory_execution_authorized": True,
        "max_cost_usd": 5.0,
        "max_provider_calls": 5000,
    }
    (data / "jar_exp_0014_execution_gate_v01.json").write_text(
        json.dumps(gate), encoding="utf-8"
    )

    result = evaluate_preflight(tmp_path)
    assert result.decision == "NO_GO"
    assert {
        "approval_typesafe_model_mismatch",
        "approval_threshold_mismatch",
        "approval_cost_ceiling_mismatch",
        "approval_call_ceiling_mismatch",
    }.issubset(set(result.blockers))


def test_calibration_receipt_must_bind_requested_model_and_provider_call_count(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    for rel in (
        "jar_exp_0014_question_contracts_v01.json",
        "jar_exp_0014_workload_plan_v01.json",
        "jar_exp_0014_critical_risk_pack_v01.json",
        "jar_exp_0014_randomization_v01.json",
    ):
        (data / rel).write_text(
            json.dumps({"status": "FROZEN_PRECALIBRATION"}), encoding="utf-8"
        )
    protocol = {"status": "FROZEN_PRECALIBRATION", "rule": "fixed"}
    (data / "jar_exp_0014_calibration_protocol_v01.json").write_text(
        json.dumps(protocol), encoding="utf-8"
    )
    (data / "calibration.json").write_text(
        json.dumps({
            "schema_version": "aftergraph.system-one-calibration/0.1",
            "experiment_id": "JAR-EXP-0014",
            "requested_model": "wrong-requested-model",
            "returned_model": "jev-test-pin",
            "corpus_sha256": calibration_corpus_sha256(build_calibration_corpus()),
            "protocol_sha256": canonical_sha256(protocol),
            "result": {
                "threshold": 0.9,
                "feasible": True,
                "critical_errors": 0,
                "total": 158,
                "critical_cases": 30,
            },
            "usage": {"provider_calls": 157, "input_tokens": 1000, "output_tokens": 200},
        }),
        encoding="utf-8",
    )
    (data / "approval.json").write_text(
        json.dumps({
            "schema_version": "aftergraph.system-one-execution-approval/0.1",
            "experiment_id": "JAR-EXP-0014",
            "approved": True,
            "network_calls_authorized": True,
            "confirmatory_execution_authorized": True,
            "returned_typesafe_model_pin": "jev-test-pin",
            "control_model_pin": "control-test-pin",
            "cascade_confidence_threshold": 0.9,
            "max_cost_usd": 5.0,
            "max_provider_calls": 5000,
            "approved_by": "test-owner",
            "approved_at": "2026-09-19T00:00:00Z",
        }),
        encoding="utf-8",
    )
    gate = {
        "requested_typesafe_model": "jev-latest",
        "returned_typesafe_model_pin": "jev-test-pin",
        "control_model_pin": "control-test-pin",
        "cascade_confidence_threshold": 0.9,
        "calibration_receipt_ref": "data/calibration.json",
        "execution_approval_ref": "data/approval.json",
        "network_calls_authorized": True,
        "confirmatory_execution_authorized": True,
        "max_cost_usd": 5.0,
        "max_provider_calls": 5000,
    }
    (data / "jar_exp_0014_execution_gate_v01.json").write_text(
        json.dumps(gate), encoding="utf-8"
    )

    result = evaluate_preflight(tmp_path)
    assert result.decision == "NO_GO"
    assert {
        "calibration_requested_model_mismatch",
        "calibration_provider_call_count_mismatch",
    }.issubset(set(result.blockers))


def test_execution_approval_requires_attributed_timezone_aware_evidence(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    for rel in (
        "jar_exp_0014_question_contracts_v01.json",
        "jar_exp_0014_workload_plan_v01.json",
        "jar_exp_0014_critical_risk_pack_v01.json",
        "jar_exp_0014_randomization_v01.json",
    ):
        (data / rel).write_text(
            json.dumps({"status": "FROZEN_PRECALIBRATION"}), encoding="utf-8"
        )

    protocol = {"status": "FROZEN_PRECALIBRATION", "rule": "fixed"}
    (data / "jar_exp_0014_calibration_protocol_v01.json").write_text(
        json.dumps(protocol), encoding="utf-8"
    )
    (data / "calibration.json").write_text(
        json.dumps({
            "schema_version": "aftergraph.system-one-calibration/0.1",
            "experiment_id": "JAR-EXP-0014",
            "requested_model": "jev-latest",
            "returned_model": "jev-test-pin",
            "corpus_sha256": calibration_corpus_sha256(build_calibration_corpus()),
            "protocol_sha256": canonical_sha256(protocol),
            "result": {
                "threshold": 0.9,
                "feasible": True,
                "critical_errors": 0,
                "total": 158,
                "critical_cases": 30,
            },
            "usage": {"provider_calls": 158, "input_tokens": 1000, "output_tokens": 200},
        }),
        encoding="utf-8",
    )
    (data / "approval.json").write_text(
        json.dumps({
            "schema_version": "aftergraph.system-one-execution-approval/0.1",
            "experiment_id": "JAR-EXP-0014",
            "approved": True,
            "network_calls_authorized": True,
            "confirmatory_execution_authorized": True,
            "returned_typesafe_model_pin": "jev-test-pin",
            "control_model_pin": "control-test-pin",
            "cascade_confidence_threshold": 0.9,
            "max_cost_usd": 5.0,
            "max_provider_calls": 5000,
            "approved_by": "   ",
            "approved_at": "2026-09-19T00:00:00",
        }),
        encoding="utf-8",
    )
    gate = {
        "requested_typesafe_model": "jev-latest",
        "returned_typesafe_model_pin": "jev-test-pin",
        "control_model_pin": "control-test-pin",
        "cascade_confidence_threshold": 0.9,
        "calibration_receipt_ref": "data/calibration.json",
        "execution_approval_ref": "data/approval.json",
        "network_calls_authorized": True,
        "confirmatory_execution_authorized": True,
        "max_cost_usd": 5.0,
        "max_provider_calls": 5000,
    }
    (data / "jar_exp_0014_execution_gate_v01.json").write_text(
        json.dumps(gate), encoding="utf-8"
    )

    result = evaluate_preflight(tmp_path)
    assert result.decision == "NO_GO"
    assert {
        "execution_approval_principal_missing",
        "execution_approval_timestamp_not_timezone_aware",
    }.issubset(set(result.blockers))
