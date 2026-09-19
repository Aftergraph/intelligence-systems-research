import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "system-one-calibration-approval-receipt.v0.1.json"


def _schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _valid_approval():
    return {
        "schema_version": "aftergraph.system-one-calibration-approval/0.1",
        "experiment_id": "JAR-EXP-0014",
        "approved": True,
        "network_calls_authorized": True,
        "requested_typesafe_model": "jev-latest",
        "calibration_manifest_sha256": "a" * 64,
        "max_cost_usd": 1.0,
        "max_provider_calls": 158,
        "approved_by": "owner-principal",
        "approved_at": "2026-09-19T00:00:00Z",
    }


def test_calibration_approval_schema_is_valid():
    jsonschema.Draft202012Validator.check_schema(_schema())


def test_calibration_approval_requires_manifest_binding():
    jsonschema.validate(instance=_valid_approval(), schema=_schema())
    approval = _valid_approval()
    del approval["calibration_manifest_sha256"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=approval, schema=_schema())


def test_calibration_approval_rejects_invalid_manifest_hash():
    approval = _valid_approval()
    approval["calibration_manifest_sha256"] = "not-a-sha"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=approval, schema=_schema())
