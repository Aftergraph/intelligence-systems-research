import json
from pathlib import Path

import jsonschema
import pytest

from experiments.system_one_acceleration.calibration import ThresholdResult
from experiments.system_one_acceleration.calibration_receipt import (
    build_calibration_receipt,
)
from experiments.system_one_acceleration.calibration_runner import (
    CalibrationObservation,
    CalibrationRunResult,
)
from experiments.system_one_acceleration.corpus import CalibrationCase


ROOT = Path(__file__).resolve().parents[1]


def _case(case_id="c1"):
    return CalibrationCase(case_id, "needs_human", {"secret": "do-not-persist"}, True, True)


def _result(case_id="c1"):
    observation = CalibrationObservation(
        case_id=case_id,
        decision_type="needs_human",
        expected=True,
        predicted=True,
        correct=True,
        critical=True,
        effective_confidence=0.99,
        returned_model="jev-1.13.0",
        latency_ms=100.0,
        input_tokens=10,
        output_tokens=2,
    )
    return CalibrationRunResult(
        requested_model="jev-latest",
        returned_model="jev-1.13.0",
        observations=(observation,),
        threshold=ThresholdResult(
            threshold=0.9,
            accepted=1,
            total=1,
            coverage=1.0,
            errors=0,
            error_rate=0.0,
            wilson_upper=0.04,
            critical_errors=0,
            feasible=True,
        ),
        provider_calls=1,
        input_tokens=10,
        output_tokens=2,
    )


def _receipt():
    return build_calibration_receipt(
        receipt_id="cal-001",
        result=_result(),
        cases=[_case()],
        protocol_document={"status": "FROZEN_PRECALIBRATION", "rule": "fixed"},
        source_commit="abcdef1",
        generated_at="2026-09-19T00:00:00Z",
    )


def test_calibration_receipt_validates_against_schema():
    schema = json.loads(
        (ROOT / "schemas" / "system-one-calibration-receipt.v0.1.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(_receipt(), schema)


def test_calibration_receipt_excludes_raw_state_and_authority_flags():
    receipt = _receipt()
    serialized = json.dumps(receipt)
    assert "do-not-persist" not in serialized
    assert "network_calls_authorized" not in serialized
    assert "confirmatory_execution_authorized" not in serialized
    assert receipt["result"]["critical_cases"] == 1


def test_calibration_receipt_requires_exact_corpus_observation_binding():
    with pytest.raises(ValueError, match="bind exactly"):
        build_calibration_receipt(
            receipt_id="cal-001",
            result=_result(case_id="different"),
            cases=[_case()],
            protocol_document={"status": "FROZEN_PRECALIBRATION"},
            source_commit="abcdef1",
            generated_at="2026-09-19T00:00:00Z",
        )
