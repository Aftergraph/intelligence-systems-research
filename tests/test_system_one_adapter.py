from types import SimpleNamespace

import pytest

from experiments.system_one_acceleration.adapter import (
    SystemOneNormalizationError,
    normalize_typesafe_answer,
    returned_model,
)


def test_normalizes_noul_without_inventing_confidence():
    answer = SimpleNamespace(type="noul", noul=0.999)
    assert normalize_typesafe_answer(answer) == {
        "kind": "noul",
        "value": 0.999,
        "confidence": None,
        "distribution": None,
    }


def test_normalizes_choice_and_preserves_distribution():
    answer = SimpleNamespace(
        type="choice",
        choice="fast",
        confidence=0.92,
        probabilities={"fast": 0.92, "powerful": 0.08},
    )
    normalized = normalize_typesafe_answer(answer)
    assert normalized["value"] == "fast"
    assert normalized["confidence"] == 0.92
    assert normalized["distribution"] == {"fast": 0.92, "powerful": 0.08}


def test_normalizes_score_without_forcing_unit_score_range():
    answer = SimpleNamespace(
        type="score",
        score=1.06,
        confidence=0.91,
        probabilities={0: 0.0, 1: 0.94, 2: 0.06},
    )
    normalized = normalize_typesafe_answer(answer)
    assert normalized["value"] == 1.06
    assert normalized["distribution"] == {"0": 0.0, "1": 0.94, "2": 0.06}


def test_rejects_distribution_that_does_not_sum_to_one():
    answer = SimpleNamespace(
        type="choice",
        choice="fast",
        confidence=0.9,
        probabilities={"fast": 0.5, "powerful": 0.2},
    )
    with pytest.raises(SystemOneNormalizationError):
        normalize_typesafe_answer(answer)


def test_rejects_choice_not_present_in_distribution():
    answer = SimpleNamespace(
        type="choice",
        choice="fast",
        confidence=0.9,
        probabilities={"powerful": 1.0},
    )
    with pytest.raises(SystemOneNormalizationError):
        normalize_typesafe_answer(answer)


def test_rejects_boolean_noul():
    with pytest.raises(SystemOneNormalizationError):
        normalize_typesafe_answer({"type": "noul", "noul": True})


def test_rejects_unknown_answer_type():
    with pytest.raises(SystemOneNormalizationError):
        normalize_typesafe_answer({"type": "text", "text": "continue"})


def test_requires_returned_model_identity():
    assert returned_model(SimpleNamespace(model="jev-1.13.0")) == "jev-1.13.0"
    with pytest.raises(SystemOneNormalizationError):
        returned_model(SimpleNamespace(model=""))
