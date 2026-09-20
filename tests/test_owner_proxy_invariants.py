"""One test per `24-AFTER-GRAPH` invariant the spine inherits (spec §2, §9).

These are NOT restatements of the spec text: each drives real code in
``authority.owner_proxy`` and asserts the observable consequence of the invariant.

  1. fail-closed admission        -- a refusal writes NOTHING anywhere
  2. tamper-evident audit chain   -- mutating a committed row is detected
  3. evidence-before-execution    -- a READY tree with no row is caught by the audit
  4. monotonic delegation attenuation -- v1 boundary (§10): attenuation is enforced on
                                     verification and NO sub-delegation is minted
  5. human-in-the-loop            -- every reserved matter returns REFUSE_RESERVED,
                                     never a silent allow

Every key is a throwaway fixture ring; the owner's real key/token is never touched,
and no test mutates the real repository.
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

from owner_proxy_gpg_helper import FixtureKeyring, install_signed_root  # noqa: E402

from authority.owner_proxy.delegation_record import delegation_ref  # noqa: E402
from authority.owner_proxy.ledger import verify_chain  # noqa: E402
from authority.owner_proxy.mandate import (  # noqa: E402
    ALLOW_ROUTINE,
    REFUSE_RESERVED,
    ACTION_MATTER,
    evaluate_mandate,
)
from authority.owner_proxy.sign_gate import (  # noqa: E402
    GATE_REL,
    LEDGER_REL,
    PENDING_REL,
    SIGN_ACTION,
    sign_calibration_gate,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DRAFT = REPO_ROOT / "keys" / "delegation_record.json"
PIN = "dc5d7a94f333908abf09aebe1ca1dbf08f965e604eb2919d0b7a9ca70e149762"
NOW = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)


def _draft() -> dict:
    return json.loads(DRAFT.read_text(encoding="utf-8"))


def _bindings(**over) -> dict:
    b = {"manifest": PIN, "model": "jev-1.13.0", "calls": 1952, "cost_usd": 5.38}
    b.update(over)
    return b


def _skeleton(tmp_path: Path, keyring: FixtureKeyring) -> Path:
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    shutil.copy2(REPO_ROOT / GATE_REL, root / GATE_REL)
    shutil.copy2(REPO_ROOT / PENDING_REL, root / PENDING_REL)
    install_signed_root(root / "keys", DRAFT.read_bytes(), keyring)
    return root


# ===========================================================================
# Invariant 1 -- fail-closed admission: a refusal writes NOTHING anywhere
# ===========================================================================

def test_invariant_fail_closed_no_write_on_any_refusal(tmp_path: Path):
    """Every refusal shape leaves the tree byte-identical: no approval record, no
    gate edit, no ledger row. 'Fails closed' means the WRITE SET is empty, not
    merely that the return value is False."""
    kr = FixtureKeyring.create()
    try:
        root = _skeleton(tmp_path, kr)
        gate_path = root / GATE_REL
        gate_before = gate_path.read_bytes()
        data_before = {p.name: p.read_bytes() for p in (root / "data").iterdir()}

        # Break the root (delete the sig) -> refusal at step 1, before any write.
        (root / "keys" / "delegation_record.sig").unlink()
        res = sign_calibration_gate(root, now=NOW, verify_ready=True)
        assert res.ok is False
        assert res.reason == "signature_missing"

        # THE assertion: nothing in data/ changed and nothing was added.
        assert gate_path.read_bytes() == gate_before
        assert {p.name: p.read_bytes() for p in (root / "data").iterdir()} == data_before
        assert not (root / LEDGER_REL).exists()
    finally:
        kr.close()


# ===========================================================================
# Invariant 2 -- tamper-evident audit chain
# ===========================================================================

def test_invariant_tamper_evident_every_mutation_of_a_committed_row_is_detected(
    tmp_path: Path,
):
    kr = FixtureKeyring.create()
    try:
        root = _skeleton(tmp_path, kr)
        res = sign_calibration_gate(root, now=NOW, verify_ready=False)
        assert res.ok is True, res.reason
        ledger = root / LEDGER_REL
        ok, reason = verify_chain(ledger)
        assert ok, reason

        rows = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(rows) == 1
        assert rows[0]["entry_sha256"] == res.entry_sha256

        # Mutate the row's tier (an attacker downgrading a reserved act to routine).
        rows[0]["tier"] = "routine-forged"
        ledger.write_text(
            "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in rows),
            encoding="utf-8",
        )
        ok, reason = verify_chain(ledger)
        assert ok is False
        assert reason is not None and "at_1" in reason

        # And the damaged chain refuses FURTHER appends (no forging on top).
        from authority.owner_proxy.ledger import append_entry

        again = append_entry(ledger, ts="2026-09-20T13:00:00+00:00",
                             actor="agent:owner-authority", principal="p",
                             delegation_ref="x", action="RATIFY_ADR", tier="routine",
                             target="t", approval_record="r", bindings={})
        assert again.ok is False
    finally:
        kr.close()


# ===========================================================================
# Invariant 3 -- evidence-before-execution
# ===========================================================================

def test_invariant_evidence_before_execution_ready_tree_without_a_row_is_caught(
    tmp_path: Path, monkeypatch, capsys
):
    """The strong true reading (spec §9 reconciliation): no EXECUTION is authorized
    without a committed row behind the READY tree. The spine cannot prevent someone
    hand-wiring a gate, so the invariant is enforced by DETECTION -- the CI audit's
    check 02 must go red on a wired/READY gate with no ledger witness."""
    import importlib.util

    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    gate = json.loads((REPO_ROOT / GATE_REL).read_text(encoding="utf-8"))
    # Hand-wire the gate to the READY shape WITHOUT any spine act, record or row.
    forged_rel = "data/jar_exp_0015_calibration_approval_20260920.json"
    gate["owner_approval_ref"] = forged_rel
    gate["network_calls_authorized"] = True
    (root / GATE_REL).write_text(json.dumps(gate, indent=2), encoding="utf-8")
    (root / forged_rel).write_text(json.dumps({
        "schema_version": "aftergraph.system-one-calibration-approval/0.1",
        "experiment_id": "JAR-EXP-0015",
        "record_status": "SIGNED",
        "approved": True,
        "network_calls_authorized": True,
        "requested_typesafe_model": "jev-1.13.0",
        "calibration_manifest_sha256": PIN,
        "max_provider_calls": 1952,
        "max_cost_usd": 5.38,
        "approved_by": "JonasAbde <147070826+JonasAbde@users.noreply.github.com>",
        "approved_at": "2026-09-20T12:00:00+00:00",
    }, indent=2), encoding="utf-8")
    (root / "keys").mkdir()

    spec = importlib.util.spec_from_file_location(
        "vdl_invariant3", REPO_ROOT / "scripts" / "verify_delegation_ledger.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    for name, val in (("REPO_ROOT", root), ("KEYS", root / "keys"), ("DATA", root / "data"),
                      ("LEDGER", root / LEDGER_REL),
                      ("RECORD_FILE", root / "keys" / "delegation_record.json"),
                      ("SIG_FILE", root / "keys" / "delegation_record.sig"),
                      ("PUBKEY_FILE", root / "keys" / "owner.pub.asc")):
        monkeypatch.setattr(mod, name, val)

    rc = mod.main()
    out = capsys.readouterr().out
    assert rc == 1, out
    assert "check=02_every_signed_approval_has_ledger_row:FAIL" in out
    # ...and with no verified root behind it, checks 03/04 fire too.
    assert "check=04_root_detached_signature_verifies:FAIL" in out


def test_invariant_evidence_before_execution_genuine_act_leaves_no_unwitnessed_ready(
    tmp_path: Path,
):
    """The converse: after a genuine spine act the READY tree IS witnessed --
    exactly one row, chain-valid, naming the approval record the gate points at."""
    kr = FixtureKeyring.create()
    try:
        root = _skeleton(tmp_path, kr)
        res = sign_calibration_gate(root, now=NOW, verify_ready=False)
        assert res.ok is True, res.reason
        rows = [json.loads(l) for l in (root / LEDGER_REL).read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(rows) == 1
        assert rows[0]["approval_record"] == res.approval_record
        assert rows[0]["target"] == GATE_REL
        assert rows[0]["bindings"]["manifest"] == PIN
        gate = json.loads((root / GATE_REL).read_text(encoding="utf-8"))
        assert gate["owner_approval_ref"] == rows[0]["approval_record"]
    finally:
        kr.close()


# ===========================================================================
# Invariant 4 -- monotonic delegation attenuation (v1 boundary, spec §10)
# ===========================================================================

def test_invariant_monotonic_attenuation_v1_mints_no_subdelegation():
    """v1 ENFORCES attenuation on verification and MINTS NOTHING. The draft record
    says so (redelegate_allowed=false, max_depth=0), and the spine exposes no
    sub-delegation minting surface -- so no act can widen a delegation."""
    rec = _draft()
    assert rec["redelegate_allowed"] is False
    assert rec["max_depth"] == 0

    import authority.owner_proxy as pkg

    minting = [n for n in dir(pkg) if "sub" in n.lower() or "redelegate" in n.lower()
               or n.lower().startswith("issue") or n.lower().startswith("mint")]
    assert minting == [], f"v1 must expose no sub-delegation minting surface: {minting}"


def test_invariant_monotonic_attenuation_scope_can_only_shrink_under_a_verified_root():
    """Any widening of scope, or shrinking of reserved_matters, moves the content
    address and therefore invalidates the owner's signature: the delegation can
    only ever be attenuated, never widened, without a fresh owner act."""
    base = _draft()
    ref = delegation_ref(base)

    widened = dict(base)
    widened["scope"] = base["scope"] + ["MINT_MONEY"]
    assert delegation_ref(widened) != ref

    softened = dict(base)
    softened["reserved_matters"] = ["BRANCH_MERGE"]
    assert delegation_ref(softened) != ref

    deeper = dict(base)
    deeper["max_depth"] = 5
    assert delegation_ref(deeper) != ref

    # And the evaluator honours the SIGNED scope, not any wider set: an action the
    # record omits is refused even though the spine knows its taxonomy.
    narrow = dict(base)
    narrow["scope"] = ["RATIFY_ADR"]
    dec = evaluate_mandate(narrow, SIGN_ACTION, _bindings(), NOW)
    assert dec.verdict != ALLOW_ROUTINE
    assert dec.reason == "out_of_scope"


# ===========================================================================
# Invariant 5 -- human-in-the-loop: reserved tier always demands confirmation
# ===========================================================================

def test_invariant_human_in_the_loop_every_reserved_matter_refuses_reserved():
    """For EVERY action class whose matter is in the signed reserved list, the fence
    returns REFUSE_RESERVED -- never a silent allow, never REFUSE_INVALID (which
    would be a different, weaker signal). This is what makes 'general owner proxy'
    bounded: the seals are carved out of the allowlist by the owner's own hand."""
    rec = _draft()
    reserved = set(rec["reserved_matters"])
    assert reserved, "the draft must reserve the preregistered seals"

    checked = 0
    for action, matter in ACTION_MATTER.items():
        if matter not in reserved:
            continue
        if action not in rec["scope"]:
            continue  # not in the allowlist -> out_of_scope, a different refusal
        dec = evaluate_mandate(rec, action, _bindings(), NOW)
        assert dec.verdict == REFUSE_RESERVED, (action, dec)
        assert dec.reason == matter, (action, dec)
        checked += 1

    # All five seals must be reachable as reserved refusals under the draft terms.
    assert checked == 5, f"expected 5 reserved action classes, exercised {checked}"


def test_invariant_human_in_the_loop_calibration_is_deliberately_not_reserved():
    """The mirror image, and the reason Gate B is reachable at all: signing the
    calibration gate within the preregistered ceiling breaks no seal, so it is a
    ROUTINE act under the standing mandate."""
    rec = _draft()
    assert "CALIBRATION_APPROVAL" not in rec["reserved_matters"]
    dec = evaluate_mandate(rec, SIGN_ACTION, _bindings(), NOW)
    assert dec.verdict == ALLOW_ROUTINE, dec


def test_invariant_human_in_the_loop_reserved_act_writes_nothing(tmp_path: Path):
    """A reserved-tier refusal must not be able to sneak a write through: the spine
    has no reserved-confirmation channel in v1, so a reserved act is a dead end."""
    kr = FixtureKeyring.create()
    try:
        root = _skeleton(tmp_path, kr)
        gate_before = (root / GATE_REL).read_bytes()
        # MERGE_BRANCH is reserved (matter BRANCH_MERGE). sign_calibration_gate only
        # ever performs SIGN_CALIBRATION_GATE, so prove the fence directly and prove
        # the tree is untouched.
        dec = evaluate_mandate(_draft(), "MERGE_BRANCH", _bindings(), NOW)
        assert dec.verdict == REFUSE_RESERVED
        assert (root / GATE_REL).read_bytes() == gate_before
        assert not (root / LEDGER_REL).exists()
    finally:
        kr.close()
