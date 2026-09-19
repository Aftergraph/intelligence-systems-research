from types import SimpleNamespace

import pytest

from experiments.system_one_acceleration.calibration_runner import (
    CalibrationRunError,
    run_calibration,
)
from experiments.system_one_acceleration.corpus import CalibrationCase
from experiments.system_one_acceleration.cost_guard import BudgetExceededError


class FakeQuestion:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeSDK:
    Noul = FakeQuestion
    Choice = FakeQuestion
    Score = FakeQuestion
    RetryPolicy = FakeQuestion


class FakeClient:
    def __init__(self, answers, models=None):
        self.answers = list(answers)
        self.models = list(models or ["jev-test-pin"] * len(self.answers))
        self.calls = 0

    def system_one(self, **kwargs):
        answer = self.answers[self.calls]
        model = self.models[self.calls]
        self.calls += 1
        key = next(iter(kwargs["questions"]))
        return SimpleNamespace(
            model=model,
            answers={key: answer},
            usage=SimpleNamespace(input_tokens=10, output_tokens=2),
        )


class FakeCostGuard:
    def __init__(self):
        self.reserved = []
        self.completed = []

    def reserve_request(self, *, request_id, decision_type, state, contract, requested_model):
        self.reserved.append(request_id)
        return SimpleNamespace(
            request_id=request_id,
            request_sha256="a" * 64,
            reserved_microusd=1,
            projected_state=dict(state),
            contract=dict(contract),
        )

    def complete_request(self, reservation, *, actual_input_tokens):
        self.completed.append((reservation.request_id, actual_input_tokens))


CONTRACTS = {
    "continue_loop": {"type": "noul", "instructions": "Continue?"},
    "route_model": {
        "type": "choice",
        "instructions": "Route.",
        "criteria": {"fast": "simple", "powerful": "hard"},
    },
    "risk_level": {
        "type": "score",
        "instructions": "Risk.",
        "criteria": ["low", "moderate", "high", "critical"],
    },
}


def test_runner_normalizes_scores_labels_and_selects_threshold():
    cases = [
        CalibrationCase("n1", "continue_loop", {"scenario": "work remains"}, True, False),
        CalibrationCase("c1", "route_model", {"scenario": "simple lookup"}, "fast", False),
        CalibrationCase("s1", "risk_level", {"scenario": "critical action"}, 3, True),
    ] * 40
    answers = []
    for _ in range(40):
        answers.extend([
            SimpleNamespace(type="noul", noul=0.99),
            SimpleNamespace(
                type="choice", choice="fast", confidence=0.99,
                probabilities={"fast": 0.99, "powerful": 0.01},
            ),
            SimpleNamespace(
                type="score", score=2.98, confidence=0.99,
                probabilities={0: 0.0, 1: 0.0, 2: 0.01, 3: 0.99},
            ),
        ])
    result = run_calibration(
        client=FakeClient(answers),
        sdk=FakeSDK,
        requested_model="jev-test-pin",
        contracts=CONTRACTS,
        cases=cases,
        maximum_calls=128,
        cost_guard=FakeCostGuard(),
    )
    assert result.provider_calls == 120
    assert result.returned_model == "jev-test-pin"
    assert result.input_tokens == 1200
    assert result.output_tokens == 240
    assert all(row.correct for row in result.observations)
    assert result.threshold.feasible is True


def test_runner_has_hard_call_ceiling_before_any_call():
    client = FakeClient([SimpleNamespace(type="noul", noul=0.99)] * 2)
    cases = [
        CalibrationCase("a", "continue_loop", {"scenario": "work remains"}, True, False),
        CalibrationCase("b", "continue_loop", {"scenario": "more work remains"}, True, False),
    ]
    with pytest.raises(CalibrationRunError, match="provider-call ceiling"):
        run_calibration(
            client=client, sdk=FakeSDK, requested_model="jev-test-pin",
            contracts=CONTRACTS, cases=cases, maximum_calls=1, cost_guard=FakeCostGuard(),
        )
    assert client.calls == 0


def test_runner_fails_on_returned_model_mismatch():
    cases = [
        CalibrationCase("a", "continue_loop", {"scenario": "work remains"}, True, False),
        CalibrationCase("b", "continue_loop", {"scenario": "more work remains"}, True, False),
    ]
    client = FakeClient(
        [SimpleNamespace(type="noul", noul=0.99)] * 2,
        models=["jev-a", "jev-b"],
    )
    with pytest.raises(CalibrationRunError, match="returned model"):
        run_calibration(
            client=client, sdk=FakeSDK, requested_model="jev-test-pin",
            contracts=CONTRACTS, cases=cases, maximum_calls=2, cost_guard=FakeCostGuard(),
        )


def test_runner_rejects_ambiguous_score_argmax():
    case = CalibrationCase("s", "risk_level", {"scenario": "high-risk action"}, 2, False)
    answer = SimpleNamespace(
        type="score", score=1.5, confidence=0.5,
        probabilities={0: 0.0, 1: 0.5, 2: 0.5, 3: 0.0},
    )
    with pytest.raises(CalibrationRunError, match="ambiguous maximum"):
        run_calibration(
            client=FakeClient([answer]), sdk=FakeSDK,
            requested_model="jev-test-pin", contracts=CONTRACTS,
            cases=[case], maximum_calls=1, cost_guard=FakeCostGuard(),
        )


def test_runner_rejects_missing_usage_evidence():
    class NoUsageClient:
        def system_one(self, **kwargs):
            key = next(iter(kwargs["questions"]))
            return SimpleNamespace(
                model="jev-test-pin",
                answers={key: SimpleNamespace(type="noul", noul=0.99)},
            )

    with pytest.raises(CalibrationRunError, match="missing token usage"):
        run_calibration(
            client=NoUsageClient(),
            sdk=FakeSDK,
            requested_model="jev-test-pin",
            contracts=CONTRACTS,
            cases=[
                CalibrationCase(
                    "a", "continue_loop", {"scenario": "work remains"}, True, False
                )
            ],
            maximum_calls=1,
            cost_guard=FakeCostGuard(),
        )


def test_cost_guard_denial_prevents_provider_transport():
    class DenyingGuard:
        def reserve_request(self, **_kwargs):
            raise BudgetExceededError("insufficient pre-request budget")

    client = FakeClient([SimpleNamespace(type="noul", noul=0.99)])
    with pytest.raises(BudgetExceededError, match="pre-request budget"):
        run_calibration(
            client=client,
            sdk=FakeSDK,
            requested_model="jev-test-pin",
            contracts=CONTRACTS,
            cases=[
                CalibrationCase(
                    "deny", "continue_loop", {"scenario": "work remains"}, True, False
                )
            ],
            maximum_calls=1,
            cost_guard=DenyingGuard(),
        )
    assert client.calls == 0
