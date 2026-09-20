"""Detached-GPG verification units for ``authority.owner_proxy.signature``.

Spec §9 "Signature round-trips with a fixture key" + "Negative / forgery tests".
Every key here is a throwaway fixture ring (tests/owner_proxy_gpg_helper.py); the
owner's real key and token are never touched. The point is to prove the VERIFIER
refuses every forgery shape, not that it can sign.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from owner_proxy_gpg_helper import FixtureKeyring  # noqa: E402

from authority.owner_proxy.signature import verify_detached_signature  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DRAFT = REPO_ROOT / "keys" / "delegation_record.json"


@pytest.fixture(scope="module")
def fixture_keyring():
    kr = FixtureKeyring.create()
    try:
        yield kr
    finally:
        kr.close()


def _record_bytes() -> bytes:
    # Use the committed draft's exact bytes so the test mirrors production.
    return DRAFT.read_bytes()


def test_good_signature_by_the_trusted_key_verifies(fixture_keyring: FixtureKeyring):
    data = _record_bytes()
    sig = fixture_keyring.sign_bytes(data)
    res = verify_detached_signature(data, sig, fixture_keyring.pubkey_armored())
    assert res.ok is True
    assert res.reason == "ok"
    assert res.signer_fingerprint == fixture_keyring.fingerprint


def test_tampering_one_byte_of_the_record_is_record_tampered(fixture_keyring: FixtureKeyring):
    data = bytearray(_record_bytes())
    sig = fixture_keyring.sign_bytes(bytes(data))
    # Flip a byte inside a value (the "hardware-token" custody string).
    idx = bytes(data).index(b"hardware-token")
    data[idx] = ord("H")  # hardware-token -> Hardware-token, signature now invalid
    res = verify_detached_signature(bytes(data), sig, fixture_keyring.pubkey_armored())
    assert res.ok is False
    assert res.reason == "record_tampered"


def test_good_signature_by_a_foreign_key_is_key_mismatch():
    owner = FixtureKeyring.create()
    attacker = FixtureKeyring.create()
    try:
        data = _record_bytes()
        # Attacker signs a perfectly well-formed record; verification is against the
        # OWNER's committed pubkey only, so the foreign signer must be refused.
        sig = attacker.sign_bytes(data)
        res = verify_detached_signature(data, sig, owner.pubkey_armored())
        assert res.ok is False
        assert res.reason == "signature_key_mismatch"
    finally:
        owner.close()
        attacker.close()


def test_missing_signature_bytes_is_signature_missing(fixture_keyring: FixtureKeyring):
    res = verify_detached_signature(_record_bytes(), b"", fixture_keyring.pubkey_armored())
    assert res.ok is False
    assert res.reason == "signature_missing"


def test_non_armored_pubkey_is_pubkey_unknown(fixture_keyring: FixtureKeyring):
    data = _record_bytes()
    sig = fixture_keyring.sign_bytes(data)
    res = verify_detached_signature(data, sig, "-----NOT A PGP KEY-----\njunk\n")
    assert res.ok is False
    assert res.reason == "pubkey_unknown"


def test_empty_record_bytes_is_record_empty(fixture_keyring: FixtureKeyring):
    sig = fixture_keyring.sign_bytes(b"")
    res = verify_detached_signature(b"", sig, fixture_keyring.pubkey_armored())
    assert res.ok is False
    assert res.reason == "record_empty"


def test_garbage_signature_bytes_is_malformed_or_key_mismatch(fixture_keyring: FixtureKeyring):
    # Random bytes that are not a parseable OpenPGP message must never verify.
    res = verify_detached_signature(_record_bytes(), b"\x80\x00not-a-signature",
                                    fixture_keyring.pubkey_armored())
    assert res.ok is False
    assert res.reason in {"signature_malformed", "signature_key_mismatch"}


def test_draft_record_is_valid_json_and_structurally_sound():
    # Guards the fixture itself: the committed draft must parse and satisfy the
    # structural validator, or every signature test would be testing garbage.
    from authority.owner_proxy.delegation_record import validate_structure

    record = json.loads(DRAFT.read_text(encoding="utf-8"))
    assert validate_structure(record) == []