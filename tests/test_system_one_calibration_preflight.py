from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.system_one_acceleration.calibration_preflight import (
    CalibrationPreflightResult,
    _is_concrete_jev_model,
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


def test_current_calibration_preflight_is_terminal_after_completed_no_threshold_run():
    result = evaluate_calibration_preflight(ROOT)
    assert result.decision == "NO_GO"
    assert result.blockers == ("calibration_already_completed",)
    assert "calibration_manifest_not_frozen" not in result.blockers
    assert "calibration_cost_hard_stop_unavailable" not in result.blockers
    assert "calibration_provider_call_ceiling_insufficient" not in result.blockers
    assert "calibration_cost_ceiling_not_frozen" not in result.blockers
    assert result.maximum_calls == 158
    assert result.maximum_cost_usd == 0.44


def test_completed_calibration_cannot_be_reauthorized_by_stale_gate_fields():
    result = evaluate_calibration_preflight(ROOT)
    assert result.decision == "NO_GO"
    assert result.blockers == ("calibration_already_completed",)


def test_guarded_calibration_refuses_rerun_before_network():
    with pytest.raises(CalibrationAuthorizationError, match="calibration_already_completed"):
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
        __import__("json").dumps({
            "status": "FROZEN_PRECALIBRATION",
            "contracts": contracts,
        }),
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

    def fake_run_durable_calibration(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(guarded_calibration, "run_durable_calibration", fake_run_durable_calibration)
    monkeypatch.setattr(
        guarded_calibration,
        "calibration_checkpoint_path",
        lambda: tmp_path / "checkpoint.json",
    )
    monkeypatch.setattr(
        guarded_calibration,
        "build_calibration_cost_guard",
        lambda **_kwargs: SimpleNamespace(
            spec=SimpleNamespace(model_id="jev-preflight-pin")
        ),
    )

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


def test_calibration_manifest_changes_when_authorized_code_changes(tmp_path):
    from experiments.system_one_acceleration.integrity import content_manifest_sha256

    first = tmp_path / "a.py"
    second = tmp_path / "b.json"
    first.write_text("one\n", encoding="utf-8")
    second.write_text('{"v":1}\n', encoding="utf-8")
    before = content_manifest_sha256(tmp_path, ("a.py", "b.json"))

    first.write_text("two\n", encoding="utf-8")
    after = content_manifest_sha256(tmp_path, ("a.py", "b.json"))

    assert before != after


def test_guarded_calibration_rejects_unfrozen_contract_document(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    contracts = {"continue_loop": {"type": "noul", "instructions": "Continue?"}}
    (data_dir / "jar_exp_0014_question_contracts_v01.json").write_text(
        __import__("json").dumps({"status": "DRAFT", "contracts": contracts}),
        encoding="utf-8",
    )
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

    with pytest.raises(CalibrationAuthorizationError, match="contracts unavailable"):
        guarded_calibration.run_authorized_calibration(
            root=tmp_path,
            client=ExplodingClient(),
            sdk=object(),
            contracts=contracts,
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("jev-1.13.0", True),
        ("jev-2.0.1", True),
        ("jev-latest", False),
        ("jev-preview", False),
        ("jev-1.13", False),
        ("", False),
        (None, False),
    ],
)
def test_calibration_requires_concrete_jev_model_pin(value, expected):
    assert _is_concrete_jev_model(value) is expected
