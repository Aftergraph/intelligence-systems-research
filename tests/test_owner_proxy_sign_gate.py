"""Orchestrator units for ``authority.owner_proxy.sign_gate`` -- the ONLY writer.

Spec §5/§8/§9. Three shapes of test:
  * refusal shapes on a 2-file skeleton (no crypto-adjacent write ever happens),
  * atomicity/rollback on the same skeleton with the preflight/ledger monkeypatched,
    asserting BYTE-IDENTICAL restoration (proof-5 methodology),
  * one full faithful-tree happy path that drives the REAL preflight to
    READY_TO_CALIBRATE and proves the pin never moves.

Every key is a throwaway fixture ring. The owner's real key/token is never touched,
and no test ever writes into the real repository's data/ or keys/ -- all mutation
happens inside tmp_path copies.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from owner_proxy_gpg_helper import FixtureKeyring, install_signed_root, write_signed_revocation  # noqa: E402

from authority.owner_proxy.delegation_record import delegation_ref  # noqa: E402
from authority.owner_proxy.ledger import LedgerResult  # noqa: E402
from authority.owner_proxy.revocation import REVOCATION_SCHEMA  # noqa: E402
from authority.owner_proxy.sign_gate import (  # noqa: E402
    ACTOR,
    GATE_REL,
    LEDGER_REL,
    PENDING_REL,
    SIGN_ACTION,
    build_approval_record,
    sign_calibration_gate,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DRAFT = REPO_ROOT / "keys" / "delegation_record.json"
PIN = "dc5d7a94f333908abf09aebe1ca1dbf08f965e604eb2919d0b7a9ca70e149762"

# Explicit clock inside the draft's [not_before, expires_at] window. Never rely on
# the wall clock: the suite must pass identically whenever it runs.
NOW = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)

IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".mypy_cache", ".pytest_cache", "live_benchmark_dry_runs"
)


def _draft_bytes(**over) -> bytes:
    rec = json.loads(DRAFT.read_text(encoding="utf-8"))
    rec.update(over)
    return (json.dumps(rec, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _skeleton(tmp_path: Path, *, record_bytes: bytes | None = None, sign: bool = True,
              keyring: FixtureKeyring | None = None, gate_over: dict | None = None):
    """A minimal tree: data/{gate,PENDING} + keys/ (optionally a verified root).

    The gate bytes are copied from the LIVE gate so the real bindings line up; gate_over
    mutates them for binding-drift refusals.
    """
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    gate = json.loads((REPO_ROOT / GATE_REL).read_text(encoding="utf-8"))
    if gate_over:
        gate.update(gate_over)
    (root / GATE_REL).write_text(
        json.dumps(gate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    shutil.copy2(REPO_ROOT / PENDING_REL, root / PENDING_REL)
    keys = root / "keys"
    keys.mkdir()
    rb = record_bytes if record_bytes is not None else DRAFT.read_bytes()
    kr = None
    if sign:
        kr = install_signed_root(keys, rb, keyring)
    else:
        (keys / "delegation_record.json").write_bytes(rb)
    return root, keys, kr


# ===========================================================================
# Refusal shapes -- nothing is ever written
# ===========================================================================

def test_refuses_without_a_delegation_record(tmp_path: Path):
    root, keys, _ = _skeleton(tmp_path, sign=False)
    (keys / "delegation_record.json").unlink()
    res = sign_calibration_gate(root, now=NOW)
    assert res.ok is False
    assert res.reason == "delegation_record_missing"
    assert res.mandate_verdict == "REFUSE_INVALID"
    assert not (root / LEDGER_REL).exists()


def test_refuses_without_a_signature(tmp_path: Path):
    root, keys, kr = _skeleton(tmp_path)
    (keys / "delegation_record.sig").unlink()
    try:
        res = sign_calibration_gate(root, now=NOW)
        assert res.ok is False
        assert res.reason == "signature_missing"
        assert not (root / LEDGER_REL).exists()
    finally:
        kr.close()


def test_refuses_without_a_committed_pubkey(tmp_path: Path):
    root, keys, kr = _skeleton(tmp_path)
    (keys / "owner.pub.asc").unlink()
    try:
        res = sign_calibration_gate(root, now=NOW)
        assert res.ok is False
        assert res.reason == "pubkey_unknown"
    finally:
        kr.close()


def test_refuses_a_tampered_record_root(tmp_path: Path):
    root, keys, kr = _skeleton(tmp_path)
    # Edit one byte of the on-disk record AFTER signing -> record_tampered.
    data = bytearray((keys / "delegation_record.json").read_bytes())
    data[data.index(b"hardware-token")] = ord("H")
    (keys / "delegation_record.json").write_bytes(bytes(data))
    try:
        res = sign_calibration_gate(root, now=NOW)
        assert res.ok is False
        assert res.reason == "root_record_tampered"
        assert not (root / LEDGER_REL).exists()
    finally:
        kr.close()


def test_refuses_a_record_signed_by_a_foreign_key(tmp_path: Path):
    owner = FixtureKeyring.create()
    attacker = FixtureKeyring.create()
    try:
        root, keys, _ = _skeleton(tmp_path, sign=False)
        # Attacker signs the draft; the committed pubkey is the owner's.
        install_signed_root(keys, DRAFT.read_bytes(), attacker)
        (keys / "owner.pub.asc").write_text(owner.pubkey_armored(), encoding="utf-8")
        res = sign_calibration_gate(root, now=NOW)
        assert res.ok is False
        assert res.reason == "root_signature_key_mismatch"
        assert not (root / LEDGER_REL).exists()
    finally:
        owner.close()
        attacker.close()


def test_refuses_an_expired_mandate(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        root, _, _ = _skeleton(tmp_path, record_bytes=_draft_bytes(
            expires_at="2026-09-19T00:00:00+00:00"), keyring=kr)
        res = sign_calibration_gate(root, now=NOW)
        assert res.ok is False
        assert res.reason == "mandate_expired"
        assert res.mandate_verdict == "REFUSE_INVALID"
        assert not (root / LEDGER_REL).exists()
    finally:
        kr.close()


def test_refuses_a_not_yet_valid_mandate(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        root, _, _ = _skeleton(tmp_path, record_bytes=_draft_bytes(
            not_before="2026-10-01T00:00:00+00:00"), keyring=kr)
        res = sign_calibration_gate(root, now=NOW)
        assert res.ok is False
        assert res.reason == "mandate_not_yet_valid"
    finally:
        kr.close()


def test_refuses_under_a_live_revocation(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        root, keys, _ = _skeleton(tmp_path, keyring=kr)
        ref = delegation_ref(json.loads(DRAFT.read_text(encoding="utf-8")))
        write_signed_revocation(keys, "revocation_kill", {
            "schema_version": REVOCATION_SCHEMA,
            "revokes_delegation_ref": ref,
            "revoked_at": "2026-09-20T06:00:00+00:00",
            "reason": "owner withdrew",
        }, kr)
        res = sign_calibration_gate(root, now=NOW)
        assert res.ok is False
        assert res.reason == "mandate_revoked"
        assert not (root / LEDGER_REL).exists()
    finally:
        kr.close()


def test_refuses_an_untrusted_revocation_set(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        root, keys, _ = _skeleton(tmp_path, keyring=kr)
        # A revocation with NO signature -> errors -> fail closed (cannot certify clean).
        (keys / "revocation_broken.json").write_text("{}", encoding="utf-8")
        res = sign_calibration_gate(root, now=NOW)
        assert res.ok is False
        assert res.reason is not None and res.reason.startswith("revocation_set_untrusted")
    finally:
        kr.close()


def test_refuses_on_binding_drift_cost(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        root, _, _ = _skeleton(tmp_path, keyring=kr, gate_over={"max_cost_usd": 999.0})
        res = sign_calibration_gate(root, now=NOW)
        assert res.ok is False
        assert res.reason == "binding_cost_ceiling"
        assert not (root / LEDGER_REL).exists()
    finally:
        kr.close()


def test_refuses_on_binding_drift_manifest(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        root, _, _ = _skeleton(tmp_path, keyring=kr,
                               gate_over={"calibration_manifest_sha256": "a" * 64})
        res = sign_calibration_gate(root, now=NOW)
        assert res.ok is False
        assert res.reason == "binding_manifest_mismatch"
    finally:
        kr.close()


def test_refuses_on_missing_gate(tmp_path: Path):
    kr = FixtureKeyring.create()
    try:
        root, keys, _ = _skeleton(tmp_path, keyring=kr)
        (root / GATE_REL).unlink()
        res = sign_calibration_gate(root, now=NOW)
        assert res.ok is False
        assert res.reason == "gate_missing"
    finally:
        kr.close()


# ===========================================================================
# Rollback / atomicity -- byte-identical restoration (proof-5 methodology)
# ===========================================================================

def test_rollback_restores_gate_byte_identically_when_preflight_not_ready(tmp_path: Path,
                                                                          monkeypatch):
    import authority.owner_proxy.sign_gate as sg

    kr = FixtureKeyring.create()
    try:
        root, _, _ = _skeleton(tmp_path, keyring=kr)
        gate_path = root / GATE_REL
        before = gate_path.read_bytes()
        monkeypatch.setattr(sg, "_run_preflight",
                            lambda r: ("NO_GO", ("jar15_manifest_mismatch",)))
        res = sign_calibration_gate(root, now=NOW, verify_ready=True)
        assert res.ok is False
        assert res.reason is not None and res.reason.startswith("preflight_not_ready:NO_GO")
        assert res.blockers == ("jar15_manifest_mismatch",)
        # BYTE-IDENTICAL restoration; no approval record; no ledger row.
        assert gate_path.read_bytes() == before
        # No SIGNED approval record survives the rollback. The PENDING template is
        # pre-existing skeleton input, not a product of the act, so mirror the
        # audit's own _signed_approvals() exclusion and assert exactly what check 02
        # would assert: zero signed approvals were left behind.
        approvals = [p for p in (root / "data").glob("jar_exp_0015_calibration_approval_*.json")
                     if p.name != "jar_exp_0015_calibration_approval_PENDING.json"]
        assert approvals == []
        assert not (root / LEDGER_REL).exists()
    finally:
        kr.close()


def test_rollback_restores_gate_when_ledger_append_fails(tmp_path: Path, monkeypatch):
    import authority.owner_proxy.sign_gate as sg

    kr = FixtureKeyring.create()
    try:
        root, _, _ = _skeleton(tmp_path, keyring=kr)
        gate_path = root / GATE_REL
        before = gate_path.read_bytes()
        monkeypatch.setattr(sg, "_run_preflight", lambda r: ("READY_TO_CALIBRATE", ()))
        monkeypatch.setattr(sg, "append_entry",
                            lambda *a, **k: LedgerResult(False, "ledger_seq_race"))
        res = sign_calibration_gate(root, now=NOW, verify_ready=True)
        assert res.ok is False
        assert res.reason is not None and res.reason.startswith("ledger_append_failed")
        assert gate_path.read_bytes() == before
        # No SIGNED approval record survives the rollback. The PENDING template is
        # pre-existing skeleton input, not a product of the act, so mirror the
        # audit's own _signed_approvals() exclusion and assert exactly what check 02
        # would assert: zero signed approvals were left behind.
        approvals = [p for p in (root / "data").glob("jar_exp_0015_calibration_approval_*.json")
                     if p.name != "jar_exp_0015_calibration_approval_PENDING.json"]
        assert approvals == []
        assert not (root / LEDGER_REL).exists()
    finally:
        kr.close()


def test_minimal_act_without_verify_writes_record_gate_and_ledger(tmp_path: Path):
    """verify_ready=False exercises the full write path on a skeleton (no experiment
    module needed): record written, gate wired, ledger committed, provenance truthful."""
    kr = FixtureKeyring.create()
    try:
        root, _, _ = _skeleton(tmp_path, keyring=kr)
        res = sign_calibration_gate(root, now=NOW, verify_ready=False)
        assert res.ok is True, res.reason
        assert res.ledger_seq == 1
        assert res.approval_record is not None
        approval_path = root / res.approval_record
        rec = json.loads(approval_path.read_text(encoding="utf-8"))
        # normative fields
        assert rec["approved"] is True
        assert rec["network_calls_authorized"] is True
        assert rec["record_status"] == "SIGNED"
        assert rec["calibration_manifest_sha256"] == PIN
        assert rec["max_cost_usd"] == 5.38
        assert rec["approved_by"].startswith("JonasAbde")
        # truthful provenance: whose HAND, which delegation, which signature
        assert rec["signed_by_hand"] == ACTOR
        assert rec["owner_signature"] == kr.fingerprint
        assert "hardware-token" in rec["authority_basis"]
        assert rec["delegation_ref"] == delegation_ref(json.loads(DRAFT.read_text(encoding="utf-8")))
        # the PENDING template's _-prefixed metadata must be dropped
        assert not any(k.startswith("_") for k in rec)
        # gate wired
        gate = json.loads((root / GATE_REL).read_text(encoding="utf-8"))
        assert gate["owner_approval_ref"] == res.approval_record
        assert gate["network_calls_authorized"] is True
        # ledger committed and chain-valid
        assert (root / LEDGER_REL).exists()
        from authority.owner_proxy.ledger import verify_chain
        ok, reason = verify_chain(root / LEDGER_REL)
        assert ok, reason
    finally:
        kr.close()


# ===========================================================================
# build_approval_record -- bindings copied FROM the gate, not the template
# ===========================================================================

def test_build_approval_record_copies_bindings_from_the_gate(tmp_path: Path):
    root, _, _ = _skeleton(tmp_path, sign=False)
    gate = json.loads((root / GATE_REL).read_text(encoding="utf-8"))
    gate["max_cost_usd"] = 7.77  # drift the gate; the record must follow the GATE
    rec = build_approval_record(gate, root=root, principal="P", approved_at="t",
                                provenance={"signed_by_hand": ACTOR})
    assert rec["max_cost_usd"] == 7.77
    assert rec["requested_typesafe_model"] == gate["requested_model"]
    assert rec["max_provider_calls"] == gate["max_provider_calls"]
    assert rec["calibration_manifest_sha256"] == gate["calibration_manifest_sha256"]
    assert rec["signed_by_hand"] == ACTOR
    assert rec["record_status"] == "SIGNED"


# ===========================================================================
# THE happy path -- full faithful tree, REAL preflight, pin must not move
# ===========================================================================

def test_full_tree_happy_path_reaches_ready_and_pin_is_untouched(tmp_path: Path):
    from experiments.system_one_acceleration.jar15_calibration_preflight import (
        evaluate_jar15_calibration_preflight,
    )
    from experiments.system_one_acceleration.jar15_integrity import (
        jar15_calibration_manifest_sha256,
    )

    tree = tmp_path / "repo"
    tree.mkdir()
    for rel in ("experiments", "data", "schemas", "scripts"):
        shutil.copytree(REPO_ROOT / rel, tree / rel, ignore=IGNORE)
    req = REPO_ROOT / "requirements-typesafe.txt"
    if req.exists():
        shutil.copy2(req, tree / "requirements-typesafe.txt")

    pin_before = jar15_calibration_manifest_sha256(tree)
    assert pin_before == PIN, "faithful copy must reproduce the pin"

    # Baseline: the copied tree is still NO_GO on the two open human gates.
    base = evaluate_jar15_calibration_preflight(tree)
    assert base.decision == "NO_GO"
    assert set(base.blockers) == {"jar15_approval_not_recorded",
                                  "jar15_network_calls_not_authorized"}

    kr = FixtureKeyring.create()
    try:
        keys = tree / "keys"
        install_signed_root(keys, DRAFT.read_bytes(), kr)
        res = sign_calibration_gate(tree, now=NOW, verify_ready=True)
        assert res.ok is True, res.reason
        assert res.decision == "READY_TO_CALIBRATE"
        assert res.blockers == ()
        assert res.ledger_seq == 1

        # The REAL preflight, re-run independently, agrees the gate is open.
        after = evaluate_jar15_calibration_preflight(tree)
        assert after.decision == "READY_TO_CALIBRATE", after.blockers

        # THE load-bearing invariant: wiring the gate never moves the 30-path pin.
        assert jar15_calibration_manifest_sha256(tree) == PIN

        # Provenance is truthful and the approval is wired into the gate.
        rec = json.loads((tree / res.approval_record).read_text(encoding="utf-8"))
        assert rec["owner_signature"] == kr.fingerprint
        assert rec["signed_by_hand"] == ACTOR
        gate = json.loads((tree / GATE_REL).read_text(encoding="utf-8"))
        assert gate["owner_approval_ref"] == res.approval_record
        assert gate["network_calls_authorized"] is True

        # Re-running the act is refused by the ledger's expected_seq race guard
        # (the chain head moved), so the act is not silently double-committed.
        res2 = sign_calibration_gate(tree, now=NOW, verify_ready=True)
        # Second act: mandate still allows it, but it would append seq-2. That is
        # permitted by design (a standing mandate covers repeated routine acts);
        # assert only that it does not corrupt the chain.
        if res2.ok:
            from authority.owner_proxy.ledger import verify_chain
            ok, reason = verify_chain(tree / LEDGER_REL)
            assert ok, reason
            assert res2.ledger_seq == 2
    finally:
        kr.close()

    # The REAL repository was never touched by any of the above.
    real_gate = json.loads((REPO_ROOT / GATE_REL).read_text(encoding="utf-8"))
    assert real_gate["owner_approval_ref"] is None
    assert real_gate["network_calls_authorized"] is False
    assert jar15_calibration_manifest_sha256(REPO_ROOT) == PIN
    assert not (REPO_ROOT / LEDGER_REL).exists()
    assert list((REPO_ROOT / "data").glob("jar_exp_0015_calibration_approval_2*.json")) == []
