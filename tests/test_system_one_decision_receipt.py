import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "system-one-decision-receipt.v0.1.json"


def _schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _valid_receipt():
    return {
        "schema_version": "aftergraph.system-one-decision/0.1",
        "receipt_id": "s1d-test-001",
        "mission_id": "mission-test-001",
        "decision_type": "continue_loop",
        "state_sha256": "a" * 64,
        "question_contract_sha256": "b" * 64,
        "model": {
            "provider": "typesafe",
            "requested_model": "jev-latest",
            "returned_model": "jev-test-pin",
        },
        "answer": {
            "kind": "noul",
            "value": 0.97,
            "confidence": None,
            "distribution": None,
        },
        "routing": {
            "decision": "accept",
            "fallback_used": False,
            "fallback_reason": None,
            "authority_bypassed": False,
        },
        "latency_ms": 100.0,
        "cost_usd": 0.00005,
        "provenance": {
            "source_commit": "deadbee",
            "generated_at": "2026-09-19T00:00:00Z",
        },
    }


def test_system_one_decision_schema_is_valid():
    jsonschema.Draft202012Validator.check_schema(_schema())


def test_system_one_decision_receipt_accepts_typesafe_noul_shape():
    jsonschema.validate(instance=_valid_receipt(), schema=_schema())


def test_choice_requires_choice_value_distribution_and_confidence():
    receipt = _valid_receipt()
    receipt["decision_type"] = "route_model"
    receipt["answer"] = {
        "kind": "choice",
        "value": "fast",
        "confidence": 0.93,
        "distribution": {"fast": 0.93, "powerful": 0.07},
    }
    jsonschema.validate(instance=receipt, schema=_schema())


def test_noul_rejects_boolean_value_and_invented_confidence():
    receipt = _valid_receipt()
    receipt["answer"]["value"] = True
    receipt["answer"]["confidence"] = 0.94

    try:
        jsonschema.validate(instance=receipt, schema=_schema())
    except jsonschema.ValidationError:
        return

    raise AssertionError("Noul receipt must preserve probability shape without invented confidence")


def test_system_one_decision_receipt_forbids_authority_bypass():
    receipt = _valid_receipt()
    receipt["routing"]["authority_bypassed"] = True

    try:
        jsonschema.validate(instance=receipt, schema=_schema())
    except jsonschema.ValidationError:
        return

    raise AssertionError("System One receipt must never permit authority_bypassed=true")
