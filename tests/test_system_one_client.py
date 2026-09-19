from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.system_one_acceleration.client import (
    TypeSafeBoundaryError,
    build_sdk_questions,
    invoke_system_one,
    load_frozen_contracts,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "data" / "jar_exp_0014_question_contracts_v01.json"


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
        self.calls = []

    def system_one(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(model="jev-test-pin", answers={}, usage=None)


def test_loads_only_frozen_question_contracts():
    contracts = load_frozen_contracts(CONTRACTS)
    assert len(contracts) == 8


def test_builds_all_three_sdk_question_primitives():
    contracts = load_frozen_contracts(CONTRACTS)
    built = build_sdk_questions(contracts, sdk=FakeSDK)
    assert set(built) == set(contracts)
    assert "criteria" not in built["continue_loop"].kwargs
    assert isinstance(built["route_model"].kwargs["criteria"], dict)
    assert isinstance(built["risk_level"].kwargs["criteria"], list)


def test_invocation_passes_model_state_and_questions_without_retrying():
    client = FakeClient()
    response, latency_ms = invoke_system_one(
        client=client,
        state={"step": 1},
        questions={"continue_loop": object()},
        requested_model="jev-latest",
        sdk=FakeSDK,
    )
    assert response.model == "jev-test-pin"
    assert latency_ms >= 0
    assert len(client.calls) == 1
    assert client.calls[0]["model"] == "jev-latest"
    assert client.calls[0]["state"] == {"step": 1}
    assert client.calls[0]["retry"].kwargs == {"max_retries": 0}


def test_missing_returned_model_fails_closed():
    class BadClient:
        def system_one(self, **kwargs):
            return SimpleNamespace(model="")

    with pytest.raises(TypeSafeBoundaryError):
        invoke_system_one(
            client=BadClient(),
            state={},
            questions={"q": object()},
            requested_model="jev-latest",
            sdk=FakeSDK,
        )


def test_missing_sdk_dependency_has_explicit_failure(monkeypatch):
    import experiments.system_one_acceleration.client as boundary

    def fail_import(name):
        raise ImportError(name)

    monkeypatch.setattr(boundary, "import_module", fail_import)
    with pytest.raises(TypeSafeBoundaryError, match="typesafe_sdk is not installed"):
        build_sdk_questions({"q": {"type": "noul", "instructions": "yes?"}})
