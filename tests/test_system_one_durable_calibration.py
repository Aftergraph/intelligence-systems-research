from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.system_one_acceleration.calibration_runner import CalibrationObservation
from experiments.system_one_acceleration.corpus import CalibrationCase
from experiments.system_one_acceleration.cost_guard import (
    BudgetLedger,
    PreRequestCostGuard,
    load_pricing_spec,
)
from experiments.system_one_acceleration.durable_calibration import (
    CalibrationCheckpointError,
    _atomic_write_json,
    run_durable_calibration,
)


ROOT = Path(__file__).resolve().parents[1]
SPEC = load_pricing_spec(ROOT / "data" / "jar_exp_0014_typesafe_pricing_v01.json")


def pricing_fixture() -> str:
    return (
        "Jev 1.13 jev-1.13.0 Price (per Btok / per Mtok) $42 / $0.042 "
        "Context length 64k tokens per request; 32k tokens for state plus the "
        "longest question. Output tokens are free."
    )


class FakeQuestion:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeSDK:
    Noul = FakeQuestion
    Choice = FakeQuestion
    Score = FakeQuestion
    RetryPolicy = FakeQuestion


class FakeClient:
    def __init__(self):
        self.calls = 0

    def system_one(self, **kwargs):
        self.calls += 1
        key = next(iter(kwargs["questions"]))
        return SimpleNamespace(
            model="jev-1.13.0",
            answers={key: SimpleNamespace(type="noul", noul=0.99)},
            usage=SimpleNamespace(input_tokens=10, output_tokens=1),
        )


CONTRACTS = {
    "continue_loop": {"type": "noul", "instructions": "Continue?"}
}
CASES = [
    CalibrationCase("resume-a", "continue_loop", {"scenario": "work remains"}, True, False),
    CalibrationCase("resume-b", "continue_loop", {"scenario": "more work remains"}, True, False),
]


def guard(tmp_path: Path) -> PreRequestCostGuard:
    ledger = BudgetLedger(
        tmp_path / "budget.sqlite",
        run_id="durable-test",
        approved_budget_microusd=10_000,
        pricing_spec_sha256=SPEC.canonical_sha256,
    )
    return PreRequestCostGuard(
        spec=SPEC,
        ledger=ledger,
        pricing_fetcher=lambda _url: pricing_fixture(),
    )


def test_completed_checkpoint_resumes_without_provider_replay(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    first_client = FakeClient()
    first = run_durable_calibration(
        client=first_client,
        sdk=FakeSDK,
        requested_model="jev-1.13.0",
        contracts=CONTRACTS,
        cases=CASES,
        maximum_calls=2,
        cost_guard=guard(tmp_path),
        checkpoint_path=checkpoint,
    )
    assert first_client.calls == 2
    assert len(first.observations) == 2

    second_client = FakeClient()
    second = run_durable_calibration(
        client=second_client,
        sdk=FakeSDK,
        requested_model="jev-1.13.0",
        contracts=CONTRACTS,
        cases=CASES,
        maximum_calls=2,
        cost_guard=guard(tmp_path),
        checkpoint_path=checkpoint,
    )
    assert second_client.calls == 0
    assert second.observations == first.observations


def test_checkpoint_reconciles_transport_started_without_replay(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    g = guard(tmp_path)
    case = CASES[0]
    reservation = g.reserve_request(
        request_id=case.case_id,
        decision_type=case.decision_type,
        state=case.state,
        contract=CONTRACTS[case.decision_type],
        requested_model="jev-1.13.0",
    )
    g.begin_transport(reservation)

    observation = CalibrationObservation(
        case_id=case.case_id,
        decision_type=case.decision_type,
        expected=True,
        predicted=True,
        correct=True,
        critical=False,
        effective_confidence=0.98,
        returned_model="jev-1.13.0",
        latency_ms=1.0,
        input_tokens=10,
        output_tokens=1,
    )
    _atomic_write_json(
        checkpoint,
        {
            "schema_version": "jar-exp-0014.calibration-checkpoint/0.1",
            "run_id": "durable-test",
            "observations": {
                case.case_id: {
                    "request_sha256": reservation.request_sha256,
                    "observation": {
                        "case_id": observation.case_id,
                        "decision_type": observation.decision_type,
                        "expected": observation.expected,
                        "predicted": observation.predicted,
                        "correct": observation.correct,
                        "critical": observation.critical,
                        "effective_confidence": observation.effective_confidence,
                        "returned_model": observation.returned_model,
                        "latency_ms": observation.latency_ms,
                        "input_tokens": observation.input_tokens,
                        "output_tokens": observation.output_tokens,
                    },
                }
            },
        },
    )

    client = FakeClient()
    result = run_durable_calibration(
        client=client,
        sdk=FakeSDK,
        requested_model="jev-1.13.0",
        contracts=CONTRACTS,
        cases=[case],
        maximum_calls=1,
        cost_guard=g,
        checkpoint_path=checkpoint,
    )
    assert client.calls == 0
    assert len(result.observations) == 1
    assert g.ledger.reservation_record(case.case_id)["status"] == "COMPLETED"


def test_transport_started_without_checkpoint_fails_closed(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    g = guard(tmp_path)
    case = CASES[0]
    reservation = g.reserve_request(
        request_id=case.case_id,
        decision_type=case.decision_type,
        state=case.state,
        contract=CONTRACTS[case.decision_type],
        requested_model="jev-1.13.0",
    )
    g.begin_transport(reservation)

    client = FakeClient()
    with pytest.raises(CalibrationCheckpointError, match="ambiguous prior transport"):
        run_durable_calibration(
            client=client,
            sdk=FakeSDK,
            requested_model="jev-1.13.0",
            contracts=CONTRACTS,
            cases=[case],
            maximum_calls=1,
            cost_guard=g,
            checkpoint_path=checkpoint,
        )
    assert client.calls == 0


def test_checkpoint_with_unknown_case_is_rejected(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    _atomic_write_json(
        checkpoint,
        {
            "schema_version": "jar-exp-0014.calibration-checkpoint/0.1",
            "run_id": "durable-test",
            "observations": {"not-frozen": {}},
        },
    )
    with pytest.raises(CalibrationCheckpointError, match="outside frozen corpus"):
        run_durable_calibration(
            client=FakeClient(),
            sdk=FakeSDK,
            requested_model="jev-1.13.0",
            contracts=CONTRACTS,
            cases=CASES,
            maximum_calls=2,
            cost_guard=guard(tmp_path),
            checkpoint_path=checkpoint,
        )
