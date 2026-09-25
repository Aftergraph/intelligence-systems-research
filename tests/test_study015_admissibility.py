import copy
import json
from pathlib import Path

import pytest

from experiments.study015.admissibility import (
    AdmissibilityError,
    assert_confirmatory_admissible,
    validate_amendment,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "study015_fixtures" / "valid_envelope.json"


def live_row():
    row = json.loads(FIXTURE.read_text(encoding="utf-8"))
    row["execution_class"] = "LIVE_VALID"
    row["is_live"] = True
    return row


def gate():
    return {
        "status":"APPROVED",
        "authorize_confirmatory_execution":True,
        "approved_by":"owner",
        "approved_at":"2026-09-25T00:00:00Z",
        "protocol_sha256":"f"*64,
    }


def freeze(row):
    return {
        "status":"FROZEN",
        "implementation_fingerprint":row["implementation_fingerprint"],
        "source_heads":row["source_heads"],
    }


def test_live_record_with_pinned_identity_is_admissible():
    row = live_row()
    assert_confirmatory_admissible([row], freeze_manifest=freeze(row), owner_gate=gate())


def test_dry_run_is_never_admissible():
    row = live_row()
    row["execution_class"] = "DRY_RUN"
    row["is_live"] = False
    with pytest.raises(AdmissibilityError, match="non-live"):
        assert_confirmatory_admissible([row], freeze_manifest=freeze(row), owner_gate=gate())


def test_source_head_drift_fails_closed():
    row = live_row()
    frozen = freeze(row)
    row["source_heads"]["runtime"] = "9"*40
    with pytest.raises(AdmissibilityError, match="source-head"):
        assert_confirmatory_admissible([row], freeze_manifest=frozen, owner_gate=gate())


def test_owner_gate_is_required():
    row = live_row()
    with pytest.raises(AdmissibilityError, match="owner gate"):
        assert_confirmatory_admissible(
            [row],
            freeze_manifest=freeze(row),
            owner_gate={"status":"NOT_APPROVED","authorize_confirmatory_execution":False},
        )


def test_amendment_requires_distinct_before_after_hashes():
    amendment = {
        "id":"S15-AMD-001",
        "timestamp_utc":"2026-09-25T00:00:00Z",
        "trigger":"methodological correction",
        "description":"example",
        "before_protocol_sha256":"a"*64,
        "after_protocol_sha256":"b"*64,
    }
    validate_amendment(amendment)
    amendment["after_protocol_sha256"] = amendment["before_protocol_sha256"]
    with pytest.raises(AdmissibilityError, match="protocol change"):
        validate_amendment(amendment)
