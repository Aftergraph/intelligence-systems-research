from pathlib import Path
import json
import shutil

from experiments.system_one_acceleration.preflight import evaluate_preflight

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
    }


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

    calibration = {
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
    }
    (data / "calibration.json").write_text(json.dumps(calibration), encoding="utf-8")
    (data / "approval.json").write_text(
        json.dumps({"experiment_id": "JAR-EXP-0014", "approved": True}),
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
