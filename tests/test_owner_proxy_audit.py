"""CI-audit tests for ``scripts/verify_delegation_ledger.py`` -- the bypass detector.

Spec §8 (Bypass): the answer to bypassing the spine is DETECTION. These tests prove
the audit (a) is vacuous-green on the real repo where nothing is signed, (b) passes
all eight checks behind a genuine spine act, and (c) turns RED on every forgery
shape: a hand-written approval with no ledger row, a root signed by a foreign key,
a ledger row bound to a wrong delegation_ref, and a fixture key leaking into the
production trust set.

The audit resolves REPO_ROOT/KEYS/DATA/LEDGER/RECORD_FILE/SIG_FILE/PUBKEY_FILE as
module globals at import time, so each temp-tree test loads the module FRESH via
importlib and rebinds all seven onto the temp tree.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from owner_proxy_gpg_helper import FixtureKeyring, install_signed_root  # noqa: E402

from authority.owner_proxy.delegation_record import delegation_ref  # noqa: E402
from authority.owner_proxy.sign_gate import GATE_REL, PENDING_REL, sign_calibration_gate  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DRAFT = REPO_ROOT / "keys" / "delegation_record.json"
AUDIT_PATH = REPO_ROOT / "scripts" / "verify_delegation_ledger.py"
NOW = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)

_counter = [0]


def _load_audit(monkeypatch, root: Path | None = None):
    """Import the audit module fresh; if ``root`` is given, rebind every path global."""
    _counter[0] += 1
    spec = importlib.util.spec_from_file_location(f"vdl_{_counter[0]}", AUDIT_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    if root is not None:
        for name, val in (
            ("REPO_ROOT", root),
            ("KEYS", root / "keys"),
            ("DATA", root / "data"),
            ("LEDGER", root / "data" / "delegation_ledger.jsonl"),
            ("RECORD_FILE", root / "keys" / "delegation_record.json"),
            ("SIG_FILE", root / "keys" / "delegation_record.sig"),
            ("PUBKEY_FILE", root / "keys" / "owner.pub.asc"),
        ):
            monkeypatch.setattr(mod, name, val)
    return mod


def _skeleton(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    shutil.copy2(REPO_ROOT / GATE_REL, root / GATE_REL)
    shutil.copy2(REPO_ROOT / PENDING_REL, root / PENDING_REL)
    (root / "keys").mkdir()
    return root


def _run(mod, capsys) -> tuple[int, str]:
    rc = mod.main()
    out = capsys.readouterr().out
    return rc, out


# --- the real repo: nothing signed yet -> vacuous green ----------------------

def test_real_repo_audit_is_vacuous_green(monkeypatch, capsys):
    mod = _load_audit(monkeypatch, None)  # no rebinding: reads the real repo
    rc, out = _run(mod, capsys)
    assert rc == 0, out
    assert "vacuous" in out
    for check in ("01_ledger_chain_valid", "02_every_signed_approval_has_ledger_row",
                  "03_delegation_record_structurally_valid",
                  "04_root_detached_signature_verifies",
                  "05_ledger_rows_bind_to_verified_root",
                  "06_rows_within_mandate_window_and_unrevoked",
                  "07_record_provenance_and_bindings_match_ledger_row",
                  "08_no_test_fixture_key_in_production_trust_set"):
        assert f"check={check}:PASS" in out, check


# --- a genuine spine act passes every check ----------------------------------

def test_genuine_act_passes_all_eight_checks(tmp_path, monkeypatch, capsys):
    kr = FixtureKeyring.create()
    try:
        root = _skeleton(tmp_path)
        install_signed_root(root / "keys", DRAFT.read_bytes(), kr)
        res = sign_calibration_gate(root, now=NOW, verify_ready=False)
        assert res.ok is True, res.reason
        mod = _load_audit(monkeypatch, root)
        rc, out = _run(mod, capsys)
        assert rc == 0, out
        assert "02_every_signed_approval_has_ledger_row:PASS" in out
        assert "04_root_detached_signature_verifies:PASS" in out
        assert "07_record_provenance_and_bindings_match_ledger_row:PASS" in out
        assert "vacuous" not in out  # a real signed approval was cross-checked
    finally:
        kr.close()


# --- forgery: hand-written approval, no ledger row, no root ------------------

def test_hand_written_approval_without_ledger_is_caught(tmp_path, monkeypatch, capsys):
    root = _skeleton(tmp_path)
    forged = {
        "schema_version": "aftergraph.system-one-calibration-approval/0.1",
        "experiment_id": "JAR-EXP-0015",
        "record_status": "SIGNED",
        "approved": True,
        "network_calls_authorized": True,
        "requested_typesafe_model": "jev-1.13.0",
        "calibration_manifest_sha256": "dc5d7a94f333908abf09aebe1ca1dbf08f965e604eb2919d0b7a9ca70e149762",
        "max_provider_calls": 1952,
        "max_cost_usd": 5.38,
        "approved_by": "JonasAbde <147070826+JonasAbde@users.noreply.github.com>",
        "approved_at": "2026-09-20T12:00:00+00:00",
        "signed_by_hand": "agent:owner-authority",
        "delegation_ref": "f" * 64,
    }
    (root / "data" / "jar_exp_0015_calibration_approval_20260920.json").write_text(
        json.dumps(forged, indent=2), encoding="utf-8"
    )
    mod = _load_audit(monkeypatch, root)
    rc, out = _run(mod, capsys)
    assert rc == 1, out
    assert "check=02_every_signed_approval_has_ledger_row:FAIL" in out
    assert "check=03_delegation_record_structurally_valid:FAIL" in out
    assert "check=04_root_detached_signature_verifies:FAIL" in out


# --- forgery: root signed by a foreign key -----------------------------------

def test_root_signed_by_foreign_key_is_caught(tmp_path, monkeypatch, capsys):
    owner = FixtureKeyring.create()
    attacker = FixtureKeyring.create()
    try:
        root = _skeleton(tmp_path)
        install_signed_root(root / "keys", DRAFT.read_bytes(), attacker)
        (root / "keys" / "owner.pub.asc").write_text(owner.pubkey_armored(), encoding="utf-8")
        mod = _load_audit(monkeypatch, root)
        rc, out = _run(mod, capsys)
        assert rc == 1, out
        assert "check=04_root_detached_signature_verifies:FAIL" in out
        assert "signature_key_mismatch" in out
    finally:
        owner.close()
        attacker.close()


# --- forgery: ledger row bound to a wrong delegation_ref ---------------------

def test_ledger_row_with_wrong_delegation_ref_is_caught(tmp_path, monkeypatch, capsys):
    kr = FixtureKeyring.create()
    try:
        root = _skeleton(tmp_path)
        install_signed_root(root / "keys", DRAFT.read_bytes(), kr)
        res = sign_calibration_gate(root, now=NOW, verify_ready=False)
        assert res.ok is True, res.reason
        # Tamper the committed row's delegation_ref (breaks the row hash too, so
        # check 01 also fires -- but 05 is the binding-specific detector).
        ledger = root / "data" / "delegation_ledger.jsonl"
        rows = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
        rows[0]["delegation_ref"] = "e" * 64
        ledger.write_text(
            "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in rows),
            encoding="utf-8",
        )
        mod = _load_audit(monkeypatch, root)
        rc, out = _run(mod, capsys)
        assert rc == 1, out
        assert "check=05_ledger_rows_bind_to_verified_root:FAIL" in out
    finally:
        kr.close()


# --- forgery: a row whose ts is outside the mandate window -------------------

def test_row_outside_mandate_window_is_caught(tmp_path, monkeypatch, capsys):
    from authority.owner_proxy.ledger import append_entry

    kr = FixtureKeyring.create()
    try:
        root = _skeleton(tmp_path)
        install_signed_root(root / "keys", DRAFT.read_bytes(), kr)
        ref = delegation_ref(json.loads(DRAFT.read_text(encoding="utf-8")))
        gate = json.loads((root / GATE_REL).read_text(encoding="utf-8"))
        append_entry(
            root / "data" / "delegation_ledger.jsonl",
            ts="2027-06-01T00:00:00+00:00",  # past the draft's 2026-12-19 expiry
            actor="agent:owner-authority",
            principal="JonasAbde <147070826+JonasAbde@users.noreply.github.com>",
            delegation_ref=ref,
            action="SIGN_CALIBRATION_GATE",
            tier="routine",
            target=GATE_REL,
            approval_record="data/jar_exp_0015_calibration_approval_20270601.json",
            bindings={"manifest": gate["calibration_manifest_sha256"],
                      "model": gate["requested_model"],
                      "calls": gate["max_provider_calls"],
                      "cost_usd": gate["max_cost_usd"]},
        )
        mod = _load_audit(monkeypatch, root)
        rc, out = _run(mod, capsys)
        assert rc == 1, out
        assert "check=06_rows_within_mandate_window_and_unrevoked:FAIL" in out
        assert "after_expiry" in out
    finally:
        kr.close()


# --- trust-set separation: no fixture key in keys/ ---------------------------

def test_fixture_key_in_trust_set_is_caught(tmp_path, monkeypatch, capsys):
    root = _skeleton(tmp_path)
    (root / "keys" / "fixture_leak.asc").write_text("-----BEGIN PGP PUBLIC KEY-----\n", encoding="utf-8")
    mod = _load_audit(monkeypatch, root)
    rc, out = _run(mod, capsys)
    assert rc == 1, out
    assert "check=08_no_test_fixture_key_in_production_trust_set:FAIL" in out
    assert "fixture_leak.asc" in out


# --- the PENDING template is never counted as a signed approval --------------

def test_pending_template_is_excluded(tmp_path, monkeypatch, capsys):
    root = _skeleton(tmp_path)
    mod = _load_audit(monkeypatch, root)
    # The skeleton carries only the PENDING template -> zero signed approvals.
    assert mod._signed_approvals() == []
    rc, out = _run(mod, capsys)
    assert rc == 0, out
    assert "vacuous" in out
