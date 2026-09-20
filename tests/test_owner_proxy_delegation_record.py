"""Structural + canonicalization units for ``authority.owner_proxy.delegation_record``.

Spec §3/§4: the record is the SINGLE SOURCE OF TRUTH for the mandate's own terms,
and ``delegation_ref`` is its content address under ADR-008 canonicalization. These
tests prove (a) the committed draft is well-formed, (b) the validator fails closed on
every defect shape, (c) the ref is order-independent and mutation-sensitive, and
-- the load-bearing early warning -- (d) the draft's bindings line up with the LIVE
gate, so Gate B is reachable as a ROUTINE act the instant the owner signs.
"""

from __future__ import annotations

import json
from pathlib import Path

from authority.owner_proxy.delegation_record import (
    RECORD_SCHEMA,
    REQUIRED_FIELDS,
    DelegationRecord,
    delegation_ref,
    load_record,
    validate_structure,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DRAFT = REPO_ROOT / "keys" / "delegation_record.json"
GATE = REPO_ROOT / "data" / "jar_exp_0015_calibration_gate_v01.json"
PIN = "dc5d7a94f333908abf09aebe1ca1dbf08f965e604eb2919d0b7a9ca70e149762"


def _draft() -> dict:
    return json.loads(DRAFT.read_text(encoding="utf-8"))


# --- the committed draft ------------------------------------------------------

def test_draft_is_structurally_valid():
    assert validate_structure(_draft()) == []


def test_draft_declares_the_record_schema():
    assert _draft()["schema_version"] == RECORD_SCHEMA


def test_load_record_returns_parsed_record_plus_ref():
    rec = load_record(DRAFT)
    assert isinstance(rec, DelegationRecord)
    assert rec.raw["delegate"] == "agent:owner-authority"
    assert rec.principal.startswith("JonasAbde")
    assert rec.budget_ceiling_usd == 5.38
    assert len(rec.ref) == 64
    assert "SIGN_CALIBRATION_GATE" in rec.scope


# --- THE early warning: draft bindings line up with the live gate -------------

def test_draft_bindings_line_up_with_live_gate():
    """Proves Gate B is reachable as a ROUTINE act under the draft terms.

    If this ever goes red, the owner would sign a record whose bindings the fence
    refuses against the real gate -- the ceremony would be futile. Catching it
    here, before any signature exists, is the whole point of committing a draft.
    """
    rec = _draft()
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    eb = rec["experiment_binding"]
    assert eb["manifest"] == gate["calibration_manifest_sha256"] == PIN
    assert eb["model"] == gate["requested_model"]
    assert eb["calls"] == gate["max_provider_calls"]
    # cost boundary: ceiling >= gate cost so the mandate's `>` check passes.
    assert rec["budget_ceiling_usd"] >= gate["max_cost_usd"]
    # and the calibration matter must NOT be reserved, or the act is REFUSE_RESERVED.
    assert "SIGN_CALIBRATION_GATE" in rec["scope"]
    assert "CALIBRATION_APPROVAL" not in rec["reserved_matters"]


# --- validator fail-closed shapes --------------------------------------------

def test_missing_required_field_is_reported():
    for field in REQUIRED_FIELDS:
        rec = _draft()
        del rec[field]
        defects = validate_structure(rec)
        assert f"record_field_missing:{field}" in defects, field


def test_wrong_schema_is_record_schema_invalid():
    rec = _draft()
    rec["schema_version"] = "aftergraph.owner-proxy-delegation/9.9"
    assert "record_schema_invalid" in validate_structure(rec)


def test_empty_scope_is_record_scope_empty():
    rec = _draft()
    rec["scope"] = []
    assert "record_scope_empty" in validate_structure(rec)


def test_non_list_scope_is_record_scope_empty():
    rec = _draft()
    rec["scope"] = "SIGN_CALIBRATION_GATE"
    assert "record_scope_empty" in validate_structure(rec)


def test_non_list_reserved_matters_is_reported():
    rec = _draft()
    rec["reserved_matters"] = "BRANCH_MERGE"
    assert "record_reserved_matters_invalid" in validate_structure(rec)


def test_zero_or_negative_ceiling_is_reported():
    for bad in (0, -1.0, "5.38", True):
        rec = _draft()
        rec["budget_ceiling_usd"] = bad
        assert "record_budget_ceiling_invalid" in validate_structure(rec), bad


def test_non_string_timestamps_are_reported():
    rec = _draft()
    rec["not_before"] = 12345
    rec["expires_at"] = 12345
    defects = validate_structure(rec)
    assert "record_not_before_invalid" in defects
    assert "record_expires_at_invalid" in defects


def test_load_record_raises_value_error_on_defect(tmp_path: Path):
    bad = _draft()
    del bad["principal"]
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    try:
        load_record(p)
    except ValueError as exc:
        assert "delegation_record_invalid" in str(exc)
        assert "record_field_missing:principal" in str(exc)
    else:
        raise AssertionError("load_record must raise on a defective record")


def test_load_record_raises_on_unparseable_json(tmp_path: Path):
    p = tmp_path / "junk.json"
    p.write_text("{not json", encoding="utf-8")
    try:
        load_record(p)
    except (ValueError, json.JSONDecodeError):
        pass
    else:
        raise AssertionError("load_record must raise on unparseable JSON")


# --- delegation_ref canonicalization (ADR-008 binding) -----------------------

def test_ref_is_independent_of_key_insertion_order():
    rec = _draft()
    shuffled = {k: rec[k] for k in reversed(list(rec.keys()))}
    assert delegation_ref(rec) == delegation_ref(shuffled)


def test_ref_changes_when_any_field_changes():
    base = delegation_ref(_draft())
    for field, value in (
        ("budget_ceiling_usd", 5.39),
        ("expires_at", "2027-01-01T00:00:00+00:00"),
        ("principal", "someone-else <x@y>"),
    ):
        rec = _draft()
        rec[field] = value
        assert delegation_ref(rec) != base, field


def test_ref_changes_when_reserved_matters_shrink():
    """The integrity catch (spec §4): editing the fence moves the content address,
    so a shrunken reserved_matters list invalidates the owner's signature."""
    base = delegation_ref(_draft())
    rec = _draft()
    rec["reserved_matters"] = ["BRANCH_MERGE"]  # drop four seals
    assert delegation_ref(rec) != base


def test_ref_changes_when_scope_widens():
    base = delegation_ref(_draft())
    rec = _draft()
    rec["scope"] = rec["scope"] + ["MINT_MONEY"]
    assert delegation_ref(rec) != base


def test_ref_matches_adr008_canonicalizer_verbatim():
    """Bind to delegation.token_exchange.canonical_constraints_hash, not a copy."""
    from delegation.token_exchange import canonical_constraints_hash

    rec = _draft()
    assert delegation_ref(rec) == canonical_constraints_hash(rec)
