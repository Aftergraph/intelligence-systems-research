#!/usr/bin/env python3
"""Owner-proxy spine dry-run for JAR-EXP-0015 calibration authorization.

Purpose
-------
Companion to ``verify_gate_plumbing_dry_run.py``. That harness proves the ONLY
things between NO_GO and READY_TO_CALIBRATE are the three human gates. This one
proves the next thing: that the owner-authority spine (``authority/owner_proxy``)
closes the owner-approval + network gates **as a ROUTINE act under a standing
owner-signed mandate**, and that it refuses to do so without the owner's hand.

It drives the REAL ``sign_calibration_gate`` orchestrator against a faithful
throwaway copy of the working tree, with the REAL fail-closed preflight as the
judge, and asserts:

  1. baseline copy is NO_GO on exactly the two open human gates;
  2. WITHOUT a verified root the spine refuses (``signature_missing`` /
     ``delegation_record_missing``) and writes nothing -- the agent cannot mint;
  3. WITH a fixture-signed root the act reaches READY_TO_CALIBRATE with zero
     blockers, and the 30-path manifest pin is byte-identical before and after;
  4. the approval record's provenance is truthful (whose authority, whose hand,
     which delegation, which signature) and the ledger witnessed the act;
  5. a tampered root (one byte edited after signing) is refused ``record_tampered``;
  6. a reserved matter (branch merge) is refused ``REFUSE_RESERVED`` even under a
     valid standing mandate -- the fence is real, not decorative;
  7. the CI audit passes all eight checks behind the genuine act, and goes RED on a
     hand-written record with no ledger row;
  8. the REAL repository is untouched: gate still NO_GO, pin intact, no ledger,
     no signed approval record.

Safety contract
---------------
This script NEVER writes a real approval record, gate edit or ledger row into the
repository. Every mutation happens inside a temp directory that is deleted on
exit. The signing key is a THROWAWAY fixture generated in a temp GNUPGHOME; the
owner's real key and hardware token are never touched (spec §9). No provider call
occurs and no SDK is imported: zero-network throughout.

Requirements
------------
Python 3.11, PyJWT (for the ADR-008 canonicalizer the record binds to), and
``gpg`` on PATH. ubuntu-latest runners ship gpg preinstalled. When gpg is absent
the harness prints an explicit SKIP and exits 0 -- a missing binary is not a spine
defect and must never be misread as one.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from authority.owner_proxy.delegation_record import delegation_ref  # noqa: E402
from authority.owner_proxy.ledger import verify_chain  # noqa: E402
from authority.owner_proxy.mandate import ACTION_MATTER, REFUSE_RESERVED, evaluate_mandate  # noqa: E402
from authority.owner_proxy.sign_gate import (  # noqa: E402
    ACTOR,
    GATE_REL,
    LEDGER_REL,
    PENDING_REL,
    SIGN_ACTION,
    sign_calibration_gate,
)
from experiments.system_one_acceleration.jar15_calibration_preflight import (  # noqa: E402
    evaluate_jar15_calibration_preflight,
)
from experiments.system_one_acceleration.jar15_integrity import (  # noqa: E402
    JAR15_CALIBRATION_INTEGRITY_PATHS,
    jar15_calibration_manifest_sha256,
)

PIN = "dc5d7a94f333908abf09aebe1ca1dbf08f965e604eb2919d0b7a9ca70e149762"
DRAFT = REPO_ROOT / "keys" / "delegation_record.json"
AUDIT = REPO_ROOT / "scripts" / "verify_delegation_ledger.py"
NOW_ISO = "2026-09-20T12:00:00+00:00"
# One deterministic instant for every spine call: inside the draft's
# [not_before, expires_at] window, so the suite behaves identically whenever CI runs.
NOW = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
OPEN_GATES = {"jar15_approval_not_recorded", "jar15_network_calls_not_authorized"}

COPY_DIRS = ("experiments", "data", "schemas", "scripts")
IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".mypy_cache", ".pytest_cache", "live_benchmark_dry_runs"
)


def _gpg(homedir: Path, *args: str, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    """cwd-pinned gpg (same MSYS workaround as authority.owner_proxy.signature._gpg).

    The keyring is passed as '.' with the process cwd set to it, and every FILE
    argument is relative to it, so this behaves identically on the owner's MSYS
    box and on the Linux CI runners.
    """
    cmd = ["gpg", "--batch", "--no-tty", "--yes", "--no-permission-warning",
           "--homedir", ".", *args]
    return subprocess.run(cmd, input=stdin, capture_output=True, check=False,
                          cwd=str(homedir))


def _make_fixture_keyring() -> tuple[Path, str] | None:
    """Generate a throwaway ed25519 sign key in a temp GNUPGHOME. None if no gpg."""
    home = Path(tempfile.mkdtemp(prefix="owner-proxy-dryrun-gpg-"))
    gen = _gpg(home, "--pinentry-mode", "loopback", "--passphrase", "",
               "--quick-generate-key", "Owner-Proxy Dry-Run Fixture <dryrun@fixture>",
               "ed25519", "sign", "never")
    if gen.returncode != 0:
        shutil.rmtree(home, ignore_errors=True)
        return None
    lst = _gpg(home, "--list-keys", "--with-colons")
    fpr = None
    for line in lst.stdout.decode("utf-8", "replace").splitlines():
        parts = line.split(":")
        if len(parts) > 9 and parts[0] == "fpr":
            fpr = parts[9].upper()
            break
    if not fpr:
        shutil.rmtree(home, ignore_errors=True)
        return None
    return home, fpr


def _install_root(keys_dir: Path, home: Path, fpr: str, record_bytes: bytes) -> None:
    """Write the record, sign THOSE EXACT BYTES, then write .sig + owner.pub.asc."""
    keys_dir.mkdir(parents=True, exist_ok=True)
    (keys_dir / "delegation_record.json").write_bytes(record_bytes)
    # gpg's cwd is pinned to the keyring (the MSYS-safe invocation) and --homedir is
    # '.', so every RELATIVE file argument resolves inside ``home``. The payload must
    # therefore live there; the resulting .sig is copied out to keys_dir below.
    (home / "dryrun_payload.bin").write_bytes(record_bytes)
    sign = _gpg(home, "--pinentry-mode", "loopback", "--passphrase", "",
                "--detach-sign", "--local-user", fpr,
                "--output", "dryrun_payload.sig", "dryrun_payload.bin")
    if sign.returncode != 0:
        raise RuntimeError("fixture sign failed: " + sign.stderr.decode("utf-8", "replace"))
    (keys_dir / "delegation_record.sig").write_bytes((home / "dryrun_payload.sig").read_bytes())
    exp = _gpg(home, "--armor", "--export", fpr)
    (keys_dir / "owner.pub.asc").write_bytes(exp.stdout)
    (home / "dryrun_payload.bin").unlink(missing_ok=True)
    (home / "dryrun_payload.sig").unlink(missing_ok=True)


def _load_audit(root: Path):
    spec = importlib.util.spec_from_file_location("vdl_dryrun", AUDIT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    for name, val in (("REPO_ROOT", root), ("KEYS", root / "keys"), ("DATA", root / "data"),
                      ("LEDGER", root / LEDGER_REL),
                      ("RECORD_FILE", root / "keys" / "delegation_record.json"),
                      ("SIG_FILE", root / "keys" / "delegation_record.sig"),
                      ("PUBKEY_FILE", root / "keys" / "owner.pub.asc")):
        setattr(mod, name, val)
    return mod


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

    if shutil.which("gpg") is None:
        print("SKIP: gpg not on PATH -- the owner-proxy dry-run needs it for the root "
              "verifier. This is an environment gap, not a spine defect.")
        print("verdict=SKIP checks=0/12")
        return 0
    if not DRAFT.exists():
        print(f"FAIL: {DRAFT} missing -- the unsigned draft record is required input")
        return 1

    fixture = _make_fixture_keyring()
    if fixture is None:
        print("SKIP: fixture keygen failed (gpg present but no agent?) -- "
              "environment gap, not a spine defect")
        print("verdict=SKIP checks=0/12")
        return 0
    gpg_home, gpg_fpr = fixture

    tmp = Path(tempfile.mkdtemp(prefix="owner-proxy-dryrun-"))
    try:
        tree = tmp / "repo"
        tree.mkdir()
        for rel in COPY_DIRS:
            shutil.copytree(REPO_ROOT / rel, tree / rel, ignore=IGNORE)
        req = REPO_ROOT / "requirements-typesafe.txt"
        if req.exists():
            shutil.copy2(req, tree / "requirements-typesafe.txt")

        missing = [p for p in JAR15_CALIBRATION_INTEGRITY_PATHS if not (tree / p).exists()]
        check("00_all_manifest_paths_present_in_temp", not missing,
              "missing=" + ",".join(missing))

        pin_copy = jar15_calibration_manifest_sha256(tree)
        check("01_manifest_reproduces_on_copy", pin_copy == PIN, f"pin={pin_copy}")

        # 02 -- BASELINE: the copy is NO_GO on exactly the two open human gates.
        base = evaluate_jar15_calibration_preflight(tree)
        check("02_baseline_no_go_on_two_open_human_gates",
              base.decision == "NO_GO" and set(base.blockers) == OPEN_GATES,
              f"decision={base.decision} blockers={'|'.join(sorted(base.blockers))}")

        # 03 -- WITHOUT a verified root the spine refuses and writes nothing.
        (tree / "keys").mkdir(exist_ok=True)
        no_root = sign_calibration_gate(tree, now=NOW)
        check("03_spine_refuses_without_a_verified_root",
              no_root.ok is False and no_root.reason in {
                  "delegation_record_missing", "signature_missing", "pubkey_unknown"},
              f"reason={no_root.reason}")
        check("04_no_write_without_a_root",
              not (tree / LEDGER_REL).exists()
              and list((tree / "data").glob("jar_exp_0015_calibration_approval_2*.json")) == []
              and json.loads((tree / GATE_REL).read_text(encoding="utf-8"))["owner_approval_ref"] is None)

        # 05 -- WITH a fixture-signed root the act reaches READY, pin unmoved.
        record_bytes = DRAFT.read_bytes()
        _install_root(tree / "keys", gpg_home, gpg_fpr, record_bytes)
        res = sign_calibration_gate(tree, now=NOW)
        check("05_routine_act_under_fixture_root_succeeds",
              res.ok is True, f"reason={res.reason}")
        check("06_real_preflight_agrees_ready",
              res.decision == "READY_TO_CALIBRATE" and res.blockers == (),
              f"decision={res.decision} blockers={'|'.join(sorted(res.blockers))}")
        indep = evaluate_jar15_calibration_preflight(tree)
        check("07_independent_preflight_rerun_agrees",
              indep.decision == "READY_TO_CALIBRATE", f"blockers={'|'.join(sorted(indep.blockers))}")
        pin_after = jar15_calibration_manifest_sha256(tree)
        check("08_pin_untouched_by_the_spine_act", pin_after == PIN, f"pin={pin_after}")

        # 09 -- truthful provenance + ledger witness.
        rec = json.loads((tree / res.approval_record).read_text(encoding="utf-8"))
        check("09_provenance_is_truthful",
              rec["signed_by_hand"] == ACTOR
              and rec["owner_signature"] == gpg_fpr
              and rec["delegation_ref"] == delegation_ref(json.loads(record_bytes.decode("utf-8")))
              and rec["approved_by"].startswith("JonasAbde")
              and "hardware-token" in rec["authority_basis"],
              f"hand={rec.get('signed_by_hand')} sig={rec.get('owner_signature')}")
        check("10_ledger_witnessed_the_act_and_chain_is_valid",
              (tree / LEDGER_REL).exists() and verify_chain(tree / LEDGER_REL)[0]
              and res.ledger_seq == 1)

        # 11 -- the CI audit passes all eight checks behind the genuine act.
        audit = _load_audit(tree)
        rc = audit.main()
        check("11_ci_audit_green_behind_a_genuine_act", rc == 0, f"audit_rc={rc}")

        # 12 -- the audit goes RED on a hand-written record with no ledger row.
        forged_tree = tmp / "forged"
        shutil.copytree(tree, forged_tree, ignore=IGNORE)
        (forged_tree / LEDGER_REL).unlink()
        (forged_tree / "keys" / "delegation_record.json").unlink(missing_ok=True)
        (forged_tree / "keys" / "delegation_record.sig").unlink(missing_ok=True)
        (forged_tree / "keys" / "owner.pub.asc").unlink(missing_ok=True)
        forged_audit = _load_audit(forged_tree)
        frc = forged_audit.main()
        check("12_ci_audit_red_on_a_hand_written_unwitnessed_record", frc == 1, f"audit_rc={frc}")

        # 13 -- a tampered root (one byte edited AFTER signing) is refused.
        tampered_tree = tmp / "tampered"
        shutil.copytree(tree, tampered_tree, ignore=IGNORE)
        (tampered_tree / LEDGER_REL).unlink()
        rp = tampered_tree / "keys" / "delegation_record.json"
        data = bytearray(rp.read_bytes())
        data[data.index(b"hardware-token")] = ord("H")
        rp.write_bytes(bytes(data))
        tres = sign_calibration_gate(tampered_tree, now=NOW)
        check("13_tampered_root_is_record_tampered",
              tres.ok is False and tres.reason == "root_record_tampered", f"reason={tres.reason}")

        # 14 -- a reserved matter is REFUSE_RESERVED under the SAME valid root.
        draft = json.loads(record_bytes.decode("utf-8"))
        reserved_seen = []
        for action, matter in ACTION_MATTER.items():
            if matter in draft["reserved_matters"] and action in draft["scope"]:
                dec = evaluate_mandate(draft, action,
                                       {"manifest": PIN, "model": "jev-1.13.0",
                                        "calls": 1952, "cost_usd": 5.38},
                                       NOW)
                if dec.verdict == REFUSE_RESERVED:
                    reserved_seen.append(action)
        check("14_reserved_matters_refuse_reserved_under_a_valid_root",
              len(reserved_seen) == 5, f"refused={','.join(sorted(reserved_seen))}")

        # 15 -- THE REAL REPOSITORY IS UNTOUCHED.
        real_gate = json.loads((REPO_ROOT / GATE_REL).read_text(encoding="utf-8"))
        real = evaluate_jar15_calibration_preflight(REPO_ROOT)
        check("15_real_tree_still_no_go",
              real.decision == "NO_GO" and set(real.blockers) == OPEN_GATES,
              f"decision={real.decision} blockers={'|'.join(sorted(real.blockers))}")
        check("16_real_pin_unchanged", jar15_calibration_manifest_sha256(REPO_ROOT) == PIN)
        check("17_real_tree_has_no_ledger_and_no_signed_approval",
              not (REPO_ROOT / LEDGER_REL).exists()
              and real_gate["owner_approval_ref"] is None
              and list((REPO_ROOT / "data").glob("jar_exp_0015_calibration_approval_2*.json")) == [])

        print()
        print("---WHAT THIS PROVES---")
        print("The owner-authority spine closes Gate B (owner approval + network")
        print("authorization) as a ROUTINE act under a standing owner-signed mandate,")
        print("without moving the 30-path calibration manifest pin, and refuses")
        print("without the owner's hand. The only act left is the owner's:")
        print("  gpg --detach-sign the committed keys/delegation_record.json")
        print("  with the hardware token, and commit keys/owner.pub.asc")
        print("  (ceremony: keys/README.md).")
        print()
        print("---EXPECT AFTER THE OWNER SIGNS---")
        print("CI verifier check 33 goes RED by design: it is a PRE-APPROVAL")
        print("snapshot asserting NO_GO with blockers subset-of human gates. Closing")
        print("Gate B makes that snapshot false. Checks 1-32 and 34-38 stay green.")

    finally:
        shutil.rmtree(gpg_home, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)

    total = 18
    print()
    if failures:
        print(f"verdict=FAIL failed={len(failures)}/{total}:" + "|".join(failures))
        return 1
    print(f"verdict=PASS checks={total}/{total}")
    print("PASS: owner-proxy spine dry-run vs real preflight (fixture root, zero-network)")
    print("falsification_attempts=18")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
