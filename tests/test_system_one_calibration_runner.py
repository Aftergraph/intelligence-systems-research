from types import SimpleNamespace

import pytest

from experiments.system_one_acceleration.calibration_runner import (
    CalibrationRunError,
    run_calibration,
)
from experiments.system_one_acceleration.corpus import CalibrationCase


class FakeQuestion:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeSDK:
    Noul = FakeQuestion
    Choice = FakeQuestion
    Score = FakeQuestion


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
        CalibrationCase("n1", "continue_loop", {"x": 1}, True, False),
        CalibrationCase("c1", "route_model", {"x": 2}, "fast", False),
        CalibrationCase("s1", "risk_level", {"x": 3}, 3, True),
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
        requested_model="jev-latest",
        contracts=CONTRACTS,
        cases=cases,
        maximum_calls=128,
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
        CalibrationCase("a", "continue_loop", {}, True, False),
        CalibrationCase("b", "continue_loop", {}, True, False),
    ]
    with pytest.raises(CalibrationRunError, match="provider-call ceiling"):
        run_calibration(
            client=client, sdk=FakeSDK, requested_model="jev-latest",
            contracts=CONTRACTS, cases=cases, maximum_calls=1,
        )
    assert client.calls == 0


def test_runner_fails_on_model_drift():
    cases = [
        CalibrationCase("a", "continue_loop", {}, True, False),
        CalibrationCase("b", "continue_loop", {}, True, False),
    ]
    client = FakeClient(
        [SimpleNamespace(type="noul", noul=0.99)] * 2,
        models=["jev-a", "jev-b"],
    )
    with pytest.raises(CalibrationRunError, match="model drift"):
        run_calibration(
            client=client, sdk=FakeSDK, requested_model="jev-latest",
            contracts=CONTRACTS, cases=cases, maximum_calls=2,
        )


def test_runner_rejects_ambiguous_score_argmax():
    case = CalibrationCase("s", "risk_level", {}, 2, False)
    answer = SimpleNamespace(
        type="score", score=1.5, confidence=0.5,
        probabilities={0: 0.0, 1: 0.5, 2: 0.5, 3: 0.0},
    )
    with pytest.raises(CalibrationRunError, match="ambiguous maximum"):
        run_calibration(
            client=FakeClient([answer]), sdk=FakeSDK,
            requested_model="jev-latest", contracts=CONTRACTS,
            cases=[case], maximum_calls=1,
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
            requested_model="jev-latest",
            contracts=CONTRACTS,
            cases=[CalibrationCase("a", "continue_loop", {}, True, False)],
            maximum_calls=1,
        )
