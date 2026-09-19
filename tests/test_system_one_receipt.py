import json

import pytest

from experiments.system_one_acceleration.receipt import (
    build_decision_receipt,
    canonical_sha256,
)


def _receipt(**overrides):
    args = {
        "receipt_id": "r-001",
        "mission_id": "m-001",
        "decision_type": "continue_loop",
        "state": {"private": "secret-value", "step": 3},
        "question_contract": {"type": "noul", "instructions": "Continue?"},
        "requested_model": "jev-latest",
        "returned_model": "jev-1.13.0",
        "answer": {
            "kind": "noul",
            "value": 0.98,
            "confidence": None,
            "distribution": None,
        },
        "routing": {
            "decision": "accept",
            "fallback_used": False,
            "fallback_reason": None,
            "authority_bypassed": False,
        },
        "source_commit": "abcdef1",
        "generated_at": "2026-09-19T00:00:00Z",
        "latency_ms": 111.0,
        "cost_usd": 0.000043,
    }
    args.update(overrides)
    return build_decision_receipt(**args)


def test_canonical_hash_ignores_mapping_order():
    assert canonical_sha256({"a": 1, "b": 2}) == canonical_sha256({"b": 2, "a": 1})


def test_receipt_persists_hashes_not_raw_state():
    receipt = _receipt()
    serialized = json.dumps(receipt)
    assert "secret-value" not in serialized
    assert receipt["state_sha256"] == canonical_sha256(
        {"private": "secret-value", "step": 3}
    )


def test_receipt_binds_question_contract():
    first = _receipt()
    second = _receipt(
        question_contract={"type": "noul", "instructions": "Stop?"}
    )
    assert first["question_contract_sha256"] != second["question_contract_sha256"]


def test_receipt_preserves_requested_and_returned_model_identity():
    receipt = _receipt()
    assert receipt["model"] == {
        "provider": "typesafe",
        "requested_model": "jev-latest",
        "returned_model": "jev-1.13.0",
    }


def test_receipt_builder_refuses_authority_bypass():
    with pytest.raises(ValueError):
        _receipt(
            routing={
                "decision": "accept",
                "fallback_used": False,
                "fallback_reason": None,
                "authority_bypassed": True,
            }
        )
