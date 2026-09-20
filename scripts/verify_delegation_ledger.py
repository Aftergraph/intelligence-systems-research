#!/usr/bin/env python3
"""Delegation-ledger CI audit -- makes a hand-forged approval record detectable.

Spec: docs/superpowers/specs/2026-09-20-owner-authority-agent-design.md (SS3, SS8, SS9).

The spine (authority/owner_proxy) is the only writer of an approval record, but it
is NOT in the loop when someone hand-writes one around it. This audit closes that
gap: every SIGNED approval record on a protected path must have a matching,
hash-chained ledger row whose delegation root (a) verifies against the single
committed owner public key, (b) was unexpired at the row timestamp, and (c) was
unrevoked at the row timestamp. A record that cannot be traced to a verified root
is a forgery, and this job fails loudly on it.

Vacuous when nothing is signed yet: zero SIGNED approval records + a valid (or
absent) ledger is GREEN. The moment a signed record appears without a verified root
behind it, this turns RED -- which is the point (spec SS8 Bypass: the answer to
bypass is detection, not prevention, and the detection is tamper-evident).

Trust set is exactly keys/owner.pub.asc. Test-only fixture keys live under tests/
and are never in keys/, so a fixture signature can never satisfy this audit
(check 08 asserts that separation).

Zero-network: reads local JSON and runs ``gpg --verify`` on a local keyring. No
provider call, no SDK import.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from authority.owner_proxy.delegation_record import delegation_ref, validate_structure  # noqa: E402
from authority.owner_proxy.ledger import verify_chain  # noqa: E402
from authority.owner_proxy.revocation import load_revocations  # noqa: E402
from authority.owner_proxy.signature import verify_detached_signature  # noqa: E402

KEYS = REPO_ROOT / "keys"
DATA = REPO_ROOT / "data"
LEDGER = DATA / "delegation_ledger.jsonl"
APPROVAL_GLOB = "jar_exp_0015_calibration_approval_*.json"
PENDING_NAME = "jar_exp_0015_calibration_approval_PENDING.json"
RECORD_FILE = KEYS / "delegation_record.json"
SIG_FILE = KEYS / "delegation_record.sig"
PUBKEY_FILE = KEYS / "owner.pub.asc"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _signed_approvals() -> list[Path]:
    """Approval records on the protected path that assert an actual approval.

    The PENDING template is unsigned (approved=false) and is excluded by name and
    by content; a record counts as SIGNED if record_status=="SIGNED" or
    approved is True.
    """
    out: list[Path] = []
    for p in sorted(DATA.glob(APPROVAL_GLOB)):
        if p.name == PENDING_NAME:
            continue
        try:
            rec = _load_json(p)
        except (OSError, json.JSONDecodeError):
            continue
        if rec.get("record_status") == "SIGNED" or rec.get("approved") is True:
            out.append(p)
    return out


def _ledger_rows() -> list[dict]:
    if not LEDGER.exists():
        return []
    rows: list[dict] = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _row_for(rows_by_record: dict, name: str) -> dict | None:
    return rows_by_record.get(name) or rows_by_record.get(f"data/{name}")


def main() -> int:
    failures: list[str] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        status = "PASS" if cond else "FAIL"
        if not cond:
            failures.append(name)
        line = f"check={name}:{status}"
        if detail:
            line += f" :: {detail}"
        print(line)

    approvals = _signed_approvals()
    rows = _ledger_rows()
    rows_by_record = {r.get("approval_record"): r for r in rows}

    # 01 -- hash-chain integrity (truncation/insertion/reorder/tamper detectable).
    chain_ok, chain_reason = (verify_chain(LEDGER) if LEDGER.exists() else (True, None))
    check("01_ledger_chain_valid", chain_ok, chain_reason or "ledger absent or valid")

    # 02 -- every signed approval record traces to a ledger row.
    unmapped = [p.name for p in approvals if _row_for(rows_by_record, p.name) is None]
    check("02_every_signed_approval_has_ledger_row", not unmapped,
          "unmapped=" + ",".join(unmapped) if unmapped else f"signed={len(approvals)}")

    # Load the root once; structural validity first.
    record = None
    ref = None
    have_root = RECORD_FILE.exists() and SIG_FILE.exists() and PUBKEY_FILE.exists()
    if have_root:
        try:
            candidate = _load_json(RECORD_FILE)
            defects = validate_structure(candidate)
            if defects:
                check("03_delegation_record_structurally_valid", False, ",".join(defects))
            else:
                record = candidate
                ref = delegation_ref(record)
                check("03_delegation_record_structurally_valid", True)
        except (OSError, json.JSONDecodeError) as exc:
            check("03_delegation_record_structurally_valid", False, str(exc))
    else:
        # No root in keys/. Vacuous iff there are no signed approvals; otherwise a
        # signed record exists that cannot be traced to any verified root -> forgery.
        check("03_delegation_record_structurally_valid", not approvals,
              "no root in keys/ but signed approvals present" if approvals
              else "no signed approvals yet (vacuous)")

    # 04 -- the root's detached signature verifies against the single committed pubkey.
    sig_ok = False
    if record is not None and have_root:
        pubkey = PUBKEY_FILE.read_text(encoding="utf-8")
        try:
            sr = verify_detached_signature(RECORD_FILE.read_bytes(), SIG_FILE.read_bytes(), pubkey)
            ok, reason = sr.ok, sr.reason
        except FileNotFoundError:
            ok, reason = False, "gpg_unavailable"
        sig_ok = ok
        check("04_root_detached_signature_verifies", ok, reason)
    else:
        check("04_root_detached_signature_verifies", not approvals,
              "no verifiable root behind signed approvals" if approvals
              else "vacuous (no signed approvals)")

    # 05 -- every ledger row binds to the verified root's delegation_ref.
    if sig_ok and ref is not None:
        bad_refs = [r.get("seq") for r in rows if r.get("delegation_ref") != ref]
        check("05_ledger_rows_bind_to_verified_root", not bad_refs,
              "bad_seqs=" + ",".join(map(str, bad_refs)) if bad_refs else f"rows={len(rows)}")
    else:
        check("05_ledger_rows_bind_to_verified_root", not rows,
              "ledger rows exist without a verified root" if rows else "vacuous")

    # 06 -- each row falls inside the mandate window and is unrevoked at its ts.
    if sig_ok and record is not None:
        pubkey = PUBKEY_FILE.read_text(encoding="utf-8")
        try:
            rev = load_revocations(KEYS, pubkey)
            rev_errs = list(rev.errors)
        except FileNotFoundError:
            rev, rev_errs = None, ["gpg_unavailable"]
        temporal_bad: list[tuple] = []
        for r in rows:
            ts = r.get("ts")
            try:
                now = _parse(ts)
            except (TypeError, ValueError):
                temporal_bad.append((r.get("seq"), "ts_unparseable"))
                continue
            nb = record.get("not_before")
            ex = record.get("expires_at")
            if isinstance(nb, str) and nb.strip() and now < _parse(nb):
                temporal_bad.append((r.get("seq"), "before_not_before"))
            if isinstance(ex, str) and ex.strip() and now > _parse(ex):
                temporal_bad.append((r.get("seq"), "after_expiry"))
            if rev is not None and rev.is_revoked(str(r.get("delegation_ref", "")), now):
                temporal_bad.append((r.get("seq"), "revoked_at_ts"))
        detail = ",".join(f"{s}:{why}" for s, why in temporal_bad)
        if rev_errs:
            detail = (detail + " reverrs=" + "|".join(rev_errs)).lstrip()
        check("06_rows_within_mandate_window_and_unrevoked",
              not temporal_bad and not rev_errs, detail or f"rows={len(rows)}")
    else:
        check("06_rows_within_mandate_window_and_unrevoked", not rows,
              "rows without verified root" if rows else "vacuous")

    # 07 -- provenance + bindings agree between each signed record and its ledger row.
    mismatch: list[tuple] = []
    for p in approvals:
        row = _row_for(rows_by_record, p.name)
        if row is None:
            continue  # already flagged by check 02
        try:
            rec = _load_json(p)
        except (OSError, json.JSONDecodeError):
            mismatch.append((p.name, "unreadable"))
            continue
        if rec.get("delegation_ref") != row.get("delegation_ref"):
            mismatch.append((p.name, "delegation_ref_mismatch"))
        if rec.get("signed_by_hand") != row.get("actor"):
            mismatch.append((p.name, "signed_by_hand_vs_actor_mismatch"))
        b = row.get("bindings", {})
        if rec.get("calibration_manifest_sha256") != b.get("manifest"):
            mismatch.append((p.name, "binding_manifest_mismatch"))
        if rec.get("requested_typesafe_model") != b.get("model"):
            mismatch.append((p.name, "binding_model_mismatch"))
        if rec.get("max_provider_calls") != b.get("calls"):
            mismatch.append((p.name, "binding_calls_mismatch"))
        if rec.get("max_cost_usd") != b.get("cost_usd"):
            mismatch.append((p.name, "binding_cost_mismatch"))
    check("07_record_provenance_and_bindings_match_ledger_row", not mismatch,
          ",".join(f"{n}:{why}" for n, why in mismatch) if mismatch
          else f"cross-checked={len(approvals)}")

    # 08 -- no test-only fixture key leaks into the production trust set.
    fixture_leak = [p.name for p in KEYS.glob("*")
                    if "fixture" in p.name.lower() or p.name.lower().startswith("test")]
    check("08_no_test_fixture_key_in_production_trust_set", not fixture_leak,
          "leaked=" + ",".join(fixture_leak) if fixture_leak else "trust set = owner.pub.asc only")

    print()
    total = 8
    if failures:
        print(f"verdict=FAIL failed={len(failures)}/{total}:" + "|".join(failures))
        return 1
    if not approvals:
        print(f"verdict=PASS checks={total}/{total} (vacuous: no signed approval records yet)")
    else:
        print(f"verdict=PASS checks={total}/{total}")
    print("PASS: delegation ledger audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())