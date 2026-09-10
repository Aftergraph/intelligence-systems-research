"""Canonical G12-9: registry alignment for STUDY-012 / ICT-EXP-0001.

TDD RED: these tests fail until the registry-alignment record exists.
They pin the pre-confirmatory amendment chain WITHOUT touching the
frozen v1.0.0 manifest (NO silent edits — see
test_no_silent_change_manifest_sha in test_study012_preconfirmatory_freeze.py).
"""

import hashlib
import json
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
REGISTRY = WORKSPACE / "data" / "study012_registry_alignment.json"
MANIFEST = WORKSPACE / "data" / "study012_workload_manifest.json"
MANIFEST_SHA_FILE = WORKSPACE / "data" / "study012_workload_manifest.json.sha256"

FROZEN_MANIFEST_SHA = "dab942d177847705385fcd18a27fec00091abfb89efdacbe8307680e39f1d218"
FROZEN_ROOT_HASH = "e5e0116105162471599707baf52d6dd5fc3b1fd39ad8265f57a71e947dc5392c"


@pytest.fixture(scope="module")
def registry():
    assert REGISTRY.is_file(), (
        "G12-9 registry alignment record missing: "
        "data/study012_registry_alignment.json"
    )
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_registry_declares_canonical_id(registry):
    """The registry declares the single canonical experiment ID."""
    assert registry.get("study_id") == "STUDY-012"
    assert registry.get("canonical_experiment_id") == "ICT-EXP-0001"


def test_registry_records_accidental_alias(registry):
    """The accidental ICT-EXP-001 (introduced via PR #79) is recorded as
    a non-canonical alias with provenance, not silently renamed."""
    aliases = registry.get("non_canonical_aliases", [])
    assert any(
        a.get("experiment_id") == "ICT-EXP-001"
        and "79" in str(a.get("introduced_via", ""))
        for a in aliases
    ), "accidental ICT-EXP-001 alias with PR #79 provenance required"


def test_amendment_chain_preserves_v100(registry):
    """The v1.0.1 pre-confirmatory amendment pins the frozen v1.0.0
    manifest and root hash byte-exactly."""
    amendments = registry.get("protocol_amendments", [])
    assert any(
        a.get("amendment_version") == "v1.0.1"
        and a.get("base_freeze_version") == "v1.0.0"
        and a.get("base_manifest_sha256") == FROZEN_MANIFEST_SHA
        and a.get("base_root_hash") == FROZEN_ROOT_HASH
        and a.get("stage") == "pre-confirmatory"
        for a in amendments
    ), "v1.0.1 amendment pinning frozen v1.0.0 by exact hashes required"


def test_manifest_v100_byte_identical():
    """The frozen v1.0.0 manifest and sidecar are untouched by G12-9."""
    assert MANIFEST.is_file() and MANIFEST_SHA_FILE.is_file()
    live = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    stored = MANIFEST_SHA_FILE.read_text(encoding="utf-8").strip().split()[0]
    assert live == FROZEN_MANIFEST_SHA == stored


def test_freeze_notice_covers_amendment(registry):
    """The effective freeze notice preserves the v1.0.0 history, states
    the v1.0.1 amendment, and keeps the NO-silent-edits invariant."""
    notice = registry.get("effective_freeze_notice", "")
    assert "v1.0.0" in notice, "v1.0.0 history must be preserved in notice"
    assert "v1.0.1" in notice, "v1.0.1 amendment must be stated in notice"
    assert "NO silent edits" in notice or "no silent" in notice.lower()


def test_no_confirmatory_claims(registry):
    """Pre-confirmatory means pre-confirmatory: no results, conclusions,
    statistics, or execution claims anywhere in the registry record."""
    blob = json.dumps(registry).lower()
    for forbidden in ("p_value", "p-value", "effect size", "conclusion:",
                      "we conclude", "execution_completed", "results_table"):
        assert forbidden not in blob, (
            f"confirmatory content forbidden pre-execution: {forbidden!r}"
        )
    assert registry.get("confirmatory_execution_occurred") is False
