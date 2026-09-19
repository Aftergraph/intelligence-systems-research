from pathlib import Path

import pytest

from experiments.system_one_acceleration.calibration_preflight import (
    CalibrationPreflightResult,
    evaluate_calibration_preflight,
)
import experiments.system_one_acceleration.guarded_calibration as guarded_calibration
from experiments.system_one_acceleration.guarded_calibration import (
    CalibrationAuthorizationError,
    run_authorized_calibration,
)


ROOT = Path(__file__).resolve().parents[1]


class ExplodingClient:
    def system_one(self, **_kwargs):
        raise AssertionError("network-capable client must not be invoked while calibration is NO_GO")


def test_current_calibration_preflight_is_fail_closed():
    result = evaluate_calibration_preflight(ROOT)
    assert result.decision == "NO_GO"
    assert {
        "calibration_provider_call_ceiling_insufficient",
        "calibration_cost_ceiling_not_frozen",
        "calibration_approval_not_recorded",
        "calibration_network_calls_not_authorized",
        "calibration_cost_hard_stop_unavailable",
    }.issubset(set(result.blockers))


def test_cost_hard_stop_blocker_is_unconditional():
    result = evaluate_calibration_preflight(ROOT)
    assert "calibration_cost_hard_stop_unavailable" in result.blockers
    assert result.decision != "READY_TO_CALIBRATE"


def test_guarded_calibration_never_reaches_client_while_no_go():
    with pytest.raises(CalibrationAuthorizationError, match="calibration not authorized"):
        run_authorized_calibration(
            root=ROOT,
            client=ExplodingClient(),
            sdk=object(),
            contracts={},
        )


def _write_frozen_contracts(root: Path, contracts: dict) -> None:
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "jar_exp_0014_question_contracts_v01.json").write_text(
        __import__("json").dumps({"contracts": contracts}),
        encoding="utf-8",
    )


def test_guarded_calibration_uses_preflight_model_without_gate_reread(tmp_path, monkeypatch):
    contracts = {"continue_loop": {"type": "noul", "instructions": "Continue?"}}
    _write_frozen_contracts(tmp_path, contracts)

    monkeypatch.setattr(
        guarded_calibration,
        "evaluate_calibration_preflight",
        lambda _root: CalibrationPreflightResult(
            decision="READY_TO_CALIBRATE",
            blockers=(),
            maximum_calls=999,
            maximum_cost_usd=1.0,
            requested_model="jev-preflight-pin",
        ),
    )
    captured = {}

    def fake_run_calibration(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(guarded_calibration, "run_calibration", fake_run_calibration)

    guarded_calibration.run_authorized_calibration(
        root=tmp_path,
        client=object(),
        sdk=object(),
        contracts=contracts,
    )

    assert captured["requested_model"] == "jev-preflight-pin"
    assert captured["maximum_calls"] == 999


def test_guarded_calibration_rejects_contract_substitution_before_client(tmp_path, monkeypatch):
    frozen = {"continue_loop": {"type": "noul", "instructions": "Continue?"}}
    _write_frozen_contracts(tmp_path, frozen)
    monkeypatch.setattr(
        guarded_calibration,
        "evaluate_calibration_preflight",
        lambda _root: CalibrationPreflightResult(
            decision="READY_TO_CALIBRATE",
            blockers=(),
            maximum_calls=999,
            maximum_cost_usd=1.0,
            requested_model="jev-preflight-pin",
        ),
    )

    with pytest.raises(CalibrationAuthorizationError, match="do not match frozen"):
        guarded_calibration.run_authorized_calibration(
            root=tmp_path,
            client=ExplodingClient(),
            sdk=object(),
            contracts={"continue_loop": {"type": "noul", "instructions": "Different?"}},
        )
