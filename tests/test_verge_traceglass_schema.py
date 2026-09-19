from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest


SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "experiments"
    / "verge_traceglass"
    / "headroom_trace.schema.json"
)

SUMMABLE_FLAG_FIELDS = ("verified_success", "false_completion")


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def compatible_record() -> dict:
    return {
        "run_id": "run-1",
        "workload_id": "workload-1",
        "confidence_threshold": 0.9,
        "verification_depth": 4,
        "retry_ceiling": 2,
        "min_confidence": 0.85,
        "min_verification": 3,
        "min_retries": 1,
        "verified_success": 1,
        "false_completion": 0,
        "unauthorized_actions": 0,
        "evidence_integrity_failures": 0,
        "cost": 1.2,
        "latency": 2.3,
        "human_interventions": 0,
        "source_artifact": "evidence/run-1.json",
        "source_hash": "abc123",
    }


def test_schema_is_a_valid_draft_2020_12_document():
    jsonschema.Draft202012Validator.check_schema(load_schema())


def test_summable_flag_record_validates():
    jsonschema.validate(compatible_record(), load_schema())


def test_label_flags_are_pinned_to_summable_zero_one_enum():
    schema = load_schema()
    for field in SUMMABLE_FLAG_FIELDS:
        prop = schema["properties"][field]
        assert prop["type"] == "integer", field
        assert prop["enum"] == [0, 1], field


@pytest.mark.parametrize("field", SUMMABLE_FLAG_FIELDS)
def test_boolean_label_is_rejected(field):
    # A JSON `true` must not pass: it would silently coexist with `0/1`
    # rows and break the summable-label invariant Headroom ranks on.
    record = compatible_record()
    record[field] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(record, load_schema())


@pytest.mark.parametrize("field", SUMMABLE_FLAG_FIELDS)
def test_non_summable_count_is_rejected(field):
    # `3` is an integer but not a 0/1 label; the enum must reject it so a
    # per-run count cannot masquerade as a fixed binary outcome.
    record = compatible_record()
    record[field] = 3
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(record, load_schema())