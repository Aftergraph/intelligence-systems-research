import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "system-one-execution-approval-receipt.v0.1.json"


def _schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _valid_approval():
    return {
        "schema_version": "aftergraph.system-one-execution-approval/0.1",
        "experiment_id": "JAR-EXP-0014",
        "approved": True,
        "network_calls_authorized": True,
        "confirmatory_execution_authorized": True,
        "returned_typesafe_model_pin": "jev-1.13.0",
        "control_model_pin": "control-model-pin",
        "cascade_confidence_threshold": 0.91,
        "execution_manifest_sha256": "a" * 64,
        "max_cost_usd": 5.0,
        "max_provider_calls": 5000,
        "approved_by": "owner-principal",
        "approved_at": "2026-09-19T00:00:00Z",
    }


def test_execution_approval_schema_is_valid_draft_2020_12():
    jsonschema.Draft202012Validator.check_schema(_schema())


def test_execution_approval_valid_example_passes():
    jsonschema.validate(instance=_valid_approval(), schema=_schema())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("approved", False),
        ("network_calls_authorized", False),
        ("confirmatory_execution_authorized", False),
        ("max_cost_usd", 0),
        ("max_provider_calls", 0),
        ("approved_by", ""),
    ],
)
def test_execution_approval_schema_fails_closed(field, value):
    approval = _valid_approval()
    approval[field] = value
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=approval, schema=_schema())


def test_execution_approval_rejects_unexpected_authority_fields():
    approval = _valid_approval()
    approval["authority_granted_by_research_repo"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=approval, schema=_schema())
