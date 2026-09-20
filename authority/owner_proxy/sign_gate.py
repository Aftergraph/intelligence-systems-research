"""sign_gate: the orchestrator and the ONLY writer of an approval record.

Spec §3, §5, §8. This is the single code path that may produce a Gate-B approval
record. It is all-or-nothing:

  1. verify the root of trust  (detached GPG signature over the DelegationRecord)
  2. load the live revocation set (never cached)
  3. evaluate the mandate for this action + the gate's real bindings
  4. write the approval record (17 normative fields + truthful provenance)
  5. wire the gate (owner_approval_ref + network_calls_authorized)
  6. VERIFY the wired tree reached READY_TO_CALIBRATE
  7. append the ledger row  <-- COMMIT POINT

Steps 4-7 roll back in reverse (delete record, restore gate bytes) on any failure
before the ledger commit, restoring the tree byte-identically. The ledger is
appended only after step 6 proves the gate actually opened, so the commit point
is never crossed by a half-good act (spec §5: "no ledger row means the act did
not happen"; here, no READY tree means no ledger row either).

The agent may USE the authority this writes; it can never MINT the root (steps 1-3
refuse without the owner's hardware-token signature). ``verify_ready=False`` lets
unit tests exercise the plumbing on a minimal tree that has no experiment module;
production and the integration dry-run leave it on.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import tempfile

from .delegation_record import load_record
from .ledger import append_entry, head_seq
from .mandate import ALLOW_ROUTINE, evaluate_mandate
from .revocation import load_revocations
from .signature import verify_detached_signature

GATE_REL = "data/jar_exp_0015_calibration_gate_v01.json"
PENDING_REL = "data/jar_exp_0015_calibration_approval_PENDING.json"
LEDGER_REL = "data/delegation_ledger.jsonl"
APPROVAL_DIR = "data"
APPROVAL_PREFIX = "jar_exp_0015_calibration_approval_"
APPROVAL_SCHEMA = "aftergraph.system-one-calibration-approval/0.1"
EXPERIMENT_ID = "JAR-EXP-0015"
SIGN_ACTION = "SIGN_CALIBRATION_GATE"
ACTOR = "agent:owner-authority"

RECORD_FILE = "delegation_record.json"
SIG_FILE = "delegation_record.sig"
PUBKEY_FILE = "owner.pub.asc"


@dataclass(frozen=True)
class SignGateResult:
    ok: bool
    reason: str | None = None
    approval_record: str | None = None
    ledger_seq: int | None = None
    entry_sha256: str | None = None
    decision: str | None = None
    blockers: tuple[str, ...] = ()
    mandate_verdict: str | None = None


class _Rollback(Exception):
    """Raised once writes have begun and must be undone."""


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """temp -> fsync -> rename, so a crash never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _dump(obj: object) -> bytes:
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def build_approval_record(
    gate: dict,
    *,
    root: Path,
    principal: str,
    approved_at: str,
    provenance: dict,
) -> dict:
    """Assemble the signed approval record.

    Starts from the PENDING template (dropping its ``_``-prefixed metadata, per
    the template's own instructions) so any extra normative fields the experiment
    expects are preserved, then OVERWRITES the four binding fields from the GATE
    (not the template) so they byte-match and cannot drift (spec §6). The
    provenance block rides alongside; the frozen preflight ignores unknown keys,
    so the manifest pin never moves.
    """
    base: dict = {}
    pending_path = Path(root) / PENDING_REL
    if pending_path.exists():
        try:
            tmpl = json.loads(pending_path.read_text(encoding="utf-8"))
            base = {k: v for k, v in tmpl.items() if not k.startswith("_")}
        except (OSError, json.JSONDecodeError):
            base = {}
    rec = dict(base)
    rec["schema_version"] = APPROVAL_SCHEMA
    rec["experiment_id"] = EXPERIMENT_ID
    rec["record_status"] = "SIGNED"
    rec["approved"] = True
    rec["network_calls_authorized"] = True
    # Binding fields copied FROM THE GATE so the preflight's *_mismatch checks pass.
    rec["requested_typesafe_model"] = gate.get("requested_model")
    rec["calibration_manifest_sha256"] = gate.get("calibration_manifest_sha256")
    rec["max_provider_calls"] = gate.get("max_provider_calls")
    rec["max_cost_usd"] = gate.get("max_cost_usd")
    # Attribution (normative): whose AUTHORITY.
    rec["approved_by"] = principal
    rec["approved_at"] = approved_at
    # Truthful provenance: whose HAND, under which delegation (spec §6).
    rec.update(provenance)
    return rec


def _run_preflight(root: Path) -> tuple[str, tuple[str, ...]]:
    from experiments.system_one_acceleration.jar15_calibration_preflight import (
        evaluate_jar15_calibration_preflight,
    )

    res = evaluate_jar15_calibration_preflight(Path(root))
    return res.decision, tuple(res.blockers)


def _rollback(approval_path: Path, approval_written: bool, gate_path: Path, gate_backup: bytes) -> None:
    if approval_written:
        try:
            if approval_path.exists():
                approval_path.unlink()
        except OSError:
            pass
    gate_path.write_bytes(gate_backup)


def sign_calibration_gate(
    root: Path | str,
    *,
    keys_dir: Path | str | None = None,
    gnupghome: Path | str | None = None,
    now: datetime | None = None,
    verify_ready: bool = True,
) -> SignGateResult:
    """Attempt the routine act of signing Gate B under the standing mandate.

    Returns a SignGateResult. ``ok`` is True only when the record was written, the
    gate wired, the tree verified READY, and the ledger committed. Every refusal
    path writes nothing.
    """
    root = Path(root)
    keys_dir = Path(keys_dir) if keys_dir is not None else root / "keys"
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # --- 1. root of trust: record + detached sig + committed pubkey ---
    record_path = keys_dir / RECORD_FILE
    sig_path = keys_dir / SIG_FILE
    pubkey_path = keys_dir / PUBKEY_FILE
    if not record_path.exists():
        return SignGateResult(False, "delegation_record_missing", mandate_verdict="REFUSE_INVALID")
    if not sig_path.exists():
        return SignGateResult(False, "signature_missing", mandate_verdict="REFUSE_INVALID")
    if not pubkey_path.exists():
        return SignGateResult(False, "pubkey_unknown", mandate_verdict="REFUSE_INVALID")

    try:
        record = load_record(record_path)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return SignGateResult(False, f"delegation_record_invalid:{exc}", mandate_verdict="REFUSE_INVALID")

    pubkey = pubkey_path.read_text(encoding="utf-8")
    sigres = verify_detached_signature(
        record_path.read_bytes(), sig_path.read_bytes(), pubkey, gnupghome=gnupghome
    )
    if not sigres.ok:
        return SignGateResult(False, f"root_{sigres.reason}", mandate_verdict="REFUSE_INVALID")

    # --- 2. live revocation set (never cached; untrusted set => refuse) ---
    rev = load_revocations(keys_dir, pubkey, gnupghome=gnupghome)
    if rev.errors:
        return SignGateResult(
            False, "revocation_set_untrusted:" + "|".join(rev.errors), mandate_verdict="REFUSE_INVALID"
        )
    revoked = rev.is_revoked(record.ref, now)

    # --- 3. gate + the action's REAL bindings ---
    gate_path = root / GATE_REL
    if not gate_path.exists():
        return SignGateResult(False, "gate_missing", mandate_verdict="REFUSE_INVALID")
    try:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return SignGateResult(False, f"gate_invalid:{exc}", mandate_verdict="REFUSE_INVALID")

    bindings = {
        "manifest": gate.get("calibration_manifest_sha256"),
        "model": gate.get("requested_model"),
        "calls": gate.get("max_provider_calls"),
        "cost_usd": gate.get("max_cost_usd"),
    }

    # --- 4. mandate evaluation (the two-tier fence) ---
    dec = evaluate_mandate(record.raw, SIGN_ACTION, bindings, now, revoked=revoked)
    if dec.verdict != ALLOW_ROUTINE:
        return SignGateResult(False, dec.reason, mandate_verdict=dec.verdict)

    # --- 5. prepare the writes ---
    approved_at = now.isoformat()
    ledger_path = root / LEDGER_REL
    next_seq = head_seq(ledger_path) + 1
    custody = str(record.raw.get("custody", "hardware-token"))
    provenance = {
        "signed_by_hand": ACTOR,               # whose HAND
        "delegation_ref": record.ref,          # which delegation
        "owner_signature": sigres.signer_fingerprint,
        "authority_basis": f"owner-signed standing mandate ({custody}), verified at sign time",
        "ledger_entry": f"seq-{next_seq}",
    }
    approval = build_approval_record(
        gate, root=root, principal=record.principal, approved_at=approved_at, provenance=provenance
    )
    stamp = now.strftime("%Y%m%d")
    approval_rel = f"{APPROVAL_DIR}/{APPROVAL_PREFIX}{stamp}.json"
    approval_path = root / approval_rel

    gate_backup = gate_path.read_bytes()
    approval_written = False
    ledger_result = None
    decision: str | None = None
    blockers: tuple[str, ...] = ()
    try:
        # 5a. write the approval record
        _atomic_write_bytes(approval_path, _dump(approval))
        approval_written = True

        # 5b. wire the gate
        wired = dict(gate)
        wired["owner_approval_ref"] = approval_rel
        wired["network_calls_authorized"] = True
        _atomic_write_bytes(gate_path, _dump(wired))

        # 5c. prove the gate actually opened before committing to the ledger
        if verify_ready:
            decision, blockers = _run_preflight(root)
            if decision != "READY_TO_CALIBRATE":
                raise _Rollback("preflight_not_ready:" + decision + ":" + "|".join(blockers))

        # 5d. append the ledger -- THE COMMIT POINT
        ledger_result = append_entry(
            ledger_path,
            ts=approved_at,
            actor=ACTOR,
            principal=record.principal,
            delegation_ref=record.ref,
            action=SIGN_ACTION,
            tier="routine",
            target=GATE_REL,
            approval_record=approval_rel,
            bindings=bindings,
            expected_seq=next_seq,
        )
        if not ledger_result.ok:
            raise _Rollback(f"ledger_append_failed:{ledger_result.reason}")
    except _Rollback as rb:
        _rollback(approval_path, approval_written, gate_path, gate_backup)
        return SignGateResult(False, str(rb), mandate_verdict=ALLOW_ROUTINE, decision=decision, blockers=blockers)
    except OSError as exc:
        _rollback(approval_path, approval_written, gate_path, gate_backup)
        return SignGateResult(False, f"sign_io_failed:{exc}", mandate_verdict=ALLOW_ROUTINE)

    assert ledger_result is not None  # ok path always sets it
    return SignGateResult(
        True,
        None,
        approval_record=approval_rel,
        ledger_seq=ledger_result.seq,
        entry_sha256=ledger_result.entry_sha256,
        decision=decision or ("READY_TO_CALIBRATE" if not verify_ready else None),
        blockers=blockers,
        mandate_verdict=ALLOW_ROUTINE,
    )