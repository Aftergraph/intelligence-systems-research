"""Revocation-set units for ``authority.owner_proxy.revocation``.

Spec §3/§8: a revocation is itself owner-signed and verified against the SAME
committed pubkey; the spine loads the set live on every act and fails closed if ANY
entry is untrusted (an untrusted revocation set cannot certify a mandate clean).
Every key here is a throwaway fixture ring; the owner's real key is never touched.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from authority.owner_proxy.delegation_record import delegation_ref
from authority.owner_proxy.revocation import (
    REVOCATION_SCHEMA,
    RevocationSet,
    load_revocations,
    revoked_refs,
)

import sys

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from owner_proxy_gpg_helper import FixtureKeyring, write_signed_revocation  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DRAFT = REPO_ROOT / "keys" / "delegation_record.json"

NOW = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
BEFORE = datetime(2026, 9, 19, 12, 0, 0, tzinfo=timezone.utc)


def _ref() -> str:
    return delegation_ref(json.loads(DRAFT.read_text(encoding="utf-8")))


def _payload(ref: str | None = None, at: str = "2026-09-20T00:00:00+00:00") -> dict:
    return {
        "schema_version": REVOCATION_SCHEMA,
        "revokes_delegation_ref": ref if ref is not None else _ref(),
        "revoked_at": at,
        "reason": "owner withdrew the mandate",
    }


# --- empty / absent -----------------------------------------------------------

def test_no_revocations_yields_empty_set_no_errors(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        keys = tmp_path / "keys"
        keys.mkdir()
        (keys / "owner.pub.asc").write_text(kr.pubkey_armored(), encoding="utf-8")
        rev = load_revocations(keys, kr.pubkey_armored())
        assert rev.poisoned == {}
        assert rev.errors == ()
        assert rev.is_revoked(_ref(), NOW) is False
    finally:
        kr.close()


def test_missing_keys_dir_glob_is_empty(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        rev = load_revocations(tmp_path / "does-not-exist", kr.pubkey_armored())
        assert rev.poisoned == {}
        assert rev.errors == ()
    finally:
        kr.close()


# --- a valid revocation poisons from its timestamp forward --------------------

def test_valid_revocation_poisons_the_ref(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        keys = tmp_path / "keys"
        write_signed_revocation(keys, "revocation_alpha", _payload(), kr)
        rev = load_revocations(keys, kr.pubkey_armored())
        assert rev.errors == ()
        assert rev.poisoned[_ref()] == "2026-09-20T00:00:00+00:00"
        assert rev.is_revoked(_ref(), NOW) is True          # now >= revoked_at
        assert rev.is_revoked(_ref(), BEFORE) is False      # before the poison date
        assert rev.is_revoked("unrelated-ref", NOW) is False
    finally:
        kr.close()


def test_earliest_revoked_at_wins_among_two_for_same_ref(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        keys = tmp_path / "keys"
        write_signed_revocation(keys, "revocation_late", _payload(at="2026-09-25T00:00:00+00:00"), kr)
        write_signed_revocation(keys, "revocation_early", _payload(at="2026-09-15T00:00:00+00:00"), kr)
        rev = load_revocations(keys, kr.pubkey_armored())
        assert rev.poisoned[_ref()] == "2026-09-15T00:00:00+00:00"
    finally:
        kr.close()


def test_unparseable_revoked_at_still_poisons_fail_closed(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        keys = tmp_path / "keys"
        write_signed_revocation(keys, "revocation_badts", _payload(at="not-a-timestamp"), kr)
        rev = load_revocations(keys, kr.pubkey_armored())
        assert rev.errors == ()  # the record itself is well-formed and signed
        assert rev.is_revoked(_ref(), BEFORE) is True  # poisons from load forward
    finally:
        kr.close()


# --- every untrusted shape surfaces as an error (caller fails closed) ---------

def test_missing_signature_is_an_error(tmp_path: Path):
    keys = tmp_path / "keys"
    keys.mkdir()
    (keys / "revocation_nosig.json").write_text(json.dumps(_payload()), encoding="utf-8")
    kr = FixtureKeyring.create()
    try:
        rev = load_revocations(keys, kr.pubkey_armored())
        assert any("revocation_signature_missing" in e for e in rev.errors)
        assert rev.poisoned == {}
    finally:
        kr.close()


def test_unparseable_json_is_an_error(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        keys = tmp_path / "keys"
        keys.mkdir()
        (keys / "revocation_junk.json").write_text("{oops", encoding="utf-8")
        (keys / "revocation_junk.json.sig").write_bytes(kr.sign_bytes(b"{oops"))
        rev = load_revocations(keys, kr.pubkey_armored())
        assert any("revocation_invalid_json" in e for e in rev.errors)
    finally:
        kr.close()


def test_wrong_schema_is_an_error(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        keys = tmp_path / "keys"
        bad = _payload()
        bad["schema_version"] = "aftergraph.owner-proxy-revocation/9.9"
        write_signed_revocation(keys, "revocation_schema", bad, kr)
        rev = load_revocations(keys, kr.pubkey_armored())
        assert any("revocation_schema_invalid" in e for e in rev.errors)
    finally:
        kr.close()


def test_missing_fields_is_an_error(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        keys = tmp_path / "keys"
        bad = _payload()
        del bad["revokes_delegation_ref"]
        write_signed_revocation(keys, "revocation_fields", bad, kr)
        rev = load_revocations(keys, kr.pubkey_armored())
        assert any("revocation_fields_missing" in e for e in rev.errors)
    finally:
        kr.close()


def test_foreign_key_signature_is_an_error(tmp_path: Path):
    owner = FixtureKeyring.create()
    attacker = FixtureKeyring.create()
    try:
        keys = tmp_path / "keys"
        # Attacker signs a perfectly well-formed revocation; verification is against
        # the OWNER's committed pubkey, so it must not be trusted.
        write_signed_revocation(keys, "revocation_foreign", _payload(), attacker)
        rev = load_revocations(keys, owner.pubkey_armored())
        assert any("revocation_signature_key_mismatch" in e for e in rev.errors)
        assert rev.poisoned == {}
    finally:
        owner.close()
        attacker.close()


def test_tampered_revocation_record_is_an_error(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        keys = tmp_path / "keys"
        path = write_signed_revocation(keys, "revocation_tamper", _payload(), kr)
        # Flip a byte after signing -> signature no longer covers the bytes.
        data = bytearray(path.read_bytes())
        data[data.index(b"withdrew")] = ord("W")
        path.write_bytes(bytes(data))
        rev = load_revocations(keys, kr.pubkey_armored())
        assert any("revocation_record_tampered" in e for e in rev.errors)
    finally:
        kr.close()


# --- the .sig fallback convention ---------------------------------------------

def test_stem_sig_fallback_is_accepted(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        keys = tmp_path / "keys"
        keys.mkdir()
        data = (json.dumps(_payload(), indent=2) + "\n").encode("utf-8")
        (keys / "revocation_fallback.json").write_bytes(data)
        # <stem>.sig (revocation_fallback.sig) instead of <name>.json.sig
        (keys / "revocation_fallback.sig").write_bytes(kr.sign_bytes(data))
        rev = load_revocations(keys, kr.pubkey_armored())
        assert rev.errors == ()
        assert _ref() in rev.poisoned
    finally:
        kr.close()


# --- RevocationSet direct semantics -------------------------------------------

def test_revocation_set_is_revoked_false_for_unknown_ref():
    rev = RevocationSet(poisoned={"x": "2026-01-01T00:00:00+00:00"})
    assert rev.is_revoked("y", NOW) is False


def test_revoked_refs_alias_matches_load(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        keys = tmp_path / "keys"
        write_signed_revocation(keys, "revocation_alias", _payload(), kr)
        a = load_revocations(keys, kr.pubkey_armored())
        b = revoked_refs(keys, kr.pubkey_armored())
        assert a.poisoned == b.poisoned
        assert a.errors == b.errors
    finally:
        kr.close()
