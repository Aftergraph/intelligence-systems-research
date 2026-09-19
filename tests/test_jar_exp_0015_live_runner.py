import json
from pathlib import Path

import pytest

from experiments.system_one_acceleration.jar15_cost_guard import (
    build_jar15_cost_guard,
)
from experiments.system_one_acceleration.jar15_durable_calibration import (
    JAR15CheckpointError,
    _atomic_write,
    _load_checkpoint,
    jar15_calibration_checkpoint_path,
)
from experiments.system_one_acceleration.jar15_live import (
    JAR15LiveError,
    load_jar15_calibration_cases,
    load_jar15_original_contracts,
)
from experiments.system_one_acceleration.jar15_preflight import (
    evaluate_jar15_stage_preflight,
)

ROOT = Path(__file__).resolve().parents[1]


def pricing_fixture() -> str:
    return (
        "Jev 1.13 jev-1.13.0 Price (per Btok / per Mtok) $42 / $0.042 "
        "Context length 64k tokens per request. Output tokens are free."
    )


def test_live_loader_uses_exact_frozen_calibration_split():
    cases = load_jar15_calibration_cases(ROOT)
    dataset = json.loads(
        (ROOT / "data" / "jar_exp_0015_dataset_v03.json").read_text(
            encoding="utf-8"
        )
    )
    expected = {
        row["case_id"]
        for row in dataset["cases"]
        if row["split"] == "calibration"
    }
    assert len(cases) == 1952
    assert {case.case_id for case in cases} == expected
    assert all(case.state.keys() == {"scenario"} for case in cases)


def test_live_loader_uses_original_contracts_only():
    contracts = load_jar15_original_contracts(ROOT)
    frozen = json.loads(
        (ROOT / "data" / "jar_exp_0015_question_contracts_v01.json").read_text(
            encoding="utf-8"
        )
    )
    assert frozen["calibration_contract_mode"] == "ORIGINAL_ONLY"
    assert contracts == frozen["original_contracts"]
    assert contracts != frozen["revised_contracts"]
    assert len(contracts) == 8


def test_calibration_guard_case_set_matches_live_loader(tmp_path):
    guard = build_jar15_cost_guard(
        root=ROOT,
        stage="calibration",
        ledger_path=tmp_path / "budget.sqlite",
        pricing_fetcher=lambda _url: pricing_fixture(),
    )
    cases = load_jar15_calibration_cases(ROOT)
    assert guard.allowed_case_ids == {case.case_id for case in cases}


def test_jar15_checkpoint_is_separate_from_jar14():
    path = jar15_calibration_checkpoint_path()
    assert "jar-exp-0015" in str(path)
    assert path.name == "abc-calibration-checkpoint-v01.json"


def test_checkpoint_round_trip_and_wrong_run_fail_closed(tmp_path):
    path = tmp_path / "checkpoint.json"
    value = {
        "schema_version": "jar-exp-0015.abc-calibration-checkpoint/0.1",
        "experiment_id": "JAR-EXP-0015",
        "stage": "A_B_C_ORIGINAL_CONTRACT_CALIBRATION",
        "run_id": "JAR-EXP-0015-calibration-v01",
        "observations": {},
    }
    _atomic_write(path, value)
    assert _load_checkpoint(
        path, run_id="JAR-EXP-0015-calibration-v01"
    ) == value
    with pytest.raises(JAR15CheckpointError, match="run mismatch"):
        _load_checkpoint(path, run_id="different-run")


def test_checkpoint_wrong_stage_fails_closed(tmp_path):
    path = tmp_path / "checkpoint.json"
    _atomic_write(
        path,
        {
            "schema_version": "jar-exp-0015.abc-calibration-checkpoint/0.1",
            "experiment_id": "JAR-EXP-0015",
            "stage": "ARM_D",
            "run_id": "JAR-EXP-0015-calibration-v01",
            "observations": {},
        },
    )
    with pytest.raises(JAR15CheckpointError, match="stage mismatch"):
        _load_checkpoint(path, run_id="JAR-EXP-0015-calibration-v01")


def test_current_live_preflight_is_ready_only_for_abc():
    result = evaluate_jar15_stage_preflight(ROOT, stage="calibration")
    assert result.decision == "READY_TO_CALIBRATE"
    assert result.blockers == ()
    assert result.maximum_calls == 1952
    assert result.maximum_cost_usd == 5.38

    arm_d = json.loads(
        (ROOT / "data" / "jar_exp_0015_arm_d_gate_v01.json").read_text(
            encoding="utf-8"
        )
    )
    holdout = json.loads(
        (ROOT / "data" / "jar_exp_0015_holdout_gate_v01.json").read_text(
            encoding="utf-8"
        )
    )
    assert arm_d["network_calls_authorized"] is False
    assert holdout["network_calls_authorized"] is False


def test_original_contract_mode_drift_fails_closed(tmp_path):
    source = ROOT / "data" / "jar_exp_0015_question_contracts_v01.json"
    value = json.loads(source.read_text(encoding="utf-8"))
    value["calibration_contract_mode"] = "REVISED"
    fake_root = tmp_path
    (fake_root / "data").mkdir()
    (fake_root / "data" / source.name).write_text(
        json.dumps(value), encoding="utf-8"
    )
    with pytest.raises(JAR15LiveError, match="contract mode drift"):
        load_jar15_original_contracts(fake_root)
