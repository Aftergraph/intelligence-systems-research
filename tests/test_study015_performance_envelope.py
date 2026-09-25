import copy
import json
from pathlib import Path

import jsonschema
import pytest

from experiments.study015.validate_envelope import (
    Study015EnvelopeError,
    load_schema,
    validate_envelope,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "study015_fixtures" / "valid_envelope.json"


def fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_schema_is_valid_draft_2020_12():
    schema = load_schema()
    jsonschema.Draft202012Validator.check_schema(schema)


def test_valid_envelope_passes_schema_and_semantic_invariants():
    assert validate_envelope(fixture())["run_id"] == "run-fixture-001"


def test_verified_success_requires_evidence_root():
    record = fixture()
    record["verification"]["evidence_root"] = None
    with pytest.raises(Study015EnvelopeError, match="evidence_root"):
        validate_envelope(record)


def test_false_completion_requires_declared_completion():
    record = fixture()
    record["outcome"].update(
        verified_success=False,
        false_completion=True,
        declared_complete=False,
    )
    record["verification"]["verdict"] = "FAIL"
    record["performance"]["time_to_verified_ms"] = None
    with pytest.raises(Study015EnvelopeError, match="declared_complete"):
        validate_envelope(record)


def test_abstention_cannot_be_hidden_as_verified_success():
    record = fixture()
    record["outcome"]["abstained"] = True
    with pytest.raises(Study015EnvelopeError, match="abstained"):
        validate_envelope(record)


def test_control_plane_tokens_cannot_exceed_total_tokens():
    record = fixture()
    record["performance"]["control_plane_tokens"] = 4201
    with pytest.raises(Study015EnvelopeError, match="control_plane_tokens"):
        validate_envelope(record)


def test_stale_authority_effect_is_a_containment_failure():
    record = fixture()
    record["authority"]["revoked_or_stale_effect_succeeded"] = True
    record["outcome"]["unauthorized_action"] = False
    with pytest.raises(Study015EnvelopeError, match="unauthorized_action"):
        validate_envelope(record)


def test_full_minus_requires_named_removed_component():
    record = fixture()
    record["condition"] = "FULL_MINUS"
    record["condition_variant"] = None
    with pytest.raises(Study015EnvelopeError, match="condition_variant"):
        validate_envelope(record)


def test_schema_rejects_bad_implementation_fingerprint():
    record = fixture()
    record["implementation_fingerprint"] = "not-a-sha256"
    with pytest.raises(jsonschema.ValidationError):
        validate_envelope(record)


def test_duplicate_or_unknown_fields_fail_closed():
    record = fixture()
    record["surprise"] = "not admitted"
    with pytest.raises(jsonschema.ValidationError):
        validate_envelope(record)


def test_dry_run_is_never_live():
    record = fixture()
    record["execution_class"] = "DRY_RUN"
    record["is_live"] = True
    with pytest.raises(jsonschema.ValidationError):
        validate_envelope(record)


def test_live_valid_must_be_live():
    record = fixture()
    record["execution_class"] = "LIVE_VALID"
    record["is_live"] = False
    with pytest.raises(jsonschema.ValidationError):
        validate_envelope(record)


def test_live_valid_fixture_variant_passes():
    record = fixture()
    record["execution_class"] = "LIVE_VALID"
    record["is_live"] = True
    assert validate_envelope(record)["execution_class"] == "LIVE_VALID"
