#!/usr/bin/env python3
"""Compatibility verifier for the frozen JAR-EXP-0015 semantic verifier.

The frozen semantic verifier is itself inside the 30-path calibration manifest and
therefore MUST NOT be edited merely because the mutable calibration gate transitions
from pre-authorization to READY_TO_CALIBRATE.

This wrapper preserves both truths:
1. Run the frozen verifier unchanged against an exact-HEAD detached worktree whose
   *excluded* calibration gate is projected back to its pre-authorization view.
2. Verify the real tree's live gate/preflight state coherently before or after Gate B.

No network calls. No owner signature operations. No manifest-path writes.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE_REL = Path("data/jar_exp_0015_calibration_gate_v01.json")
HOLDOUT_REL = Path("data/jar_exp_0015_holdout_gate_v01.json")
ANALYSIS_REL = Path("data/jar_exp_0015_analysis_gate_v01.json")
ACTIVE_REL = Path("data/jar_exp_0015_active_protocol.json")
FROZEN_VERIFIER_REL = Path("scripts/verify_jar_exp_0015_semantic_review.py")

sys.path.insert(0, str(ROOT))

from experiments.system_one_acceleration.jar15_calibration_preflight import (  # noqa: E402
    evaluate_jar15_calibration_preflight,
)
from experiments.system_one_acceleration.jar15_integrity import (  # noqa: E402
    jar15_calibration_manifest_sha256,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _open_human_gates(gate: dict) -> set[str]:
    out: set[str] = set()
    if not gate.get("semantic_review_ref"):
        out.add("jar15_semantic_review_not_recorded")
    if not gate.get("owner_approval_ref"):
        out.add("jar15_approval_not_recorded")
    if gate.get("network_calls_authorized") is not True:
        out.add("jar15_network_calls_not_authorized")
    return out


def _run_frozen_verifier() -> tuple[bool, str]:
    """Run the pinned verifier without mutating the real checkout."""
    tmp = Path(tempfile.mkdtemp(prefix="jar15-frozen-semantic-"))
    wt = tmp / "worktree"
    added = False
    try:
        add = subprocess.run(
            ["git", "-C", str(ROOT), "worktree", "add", "--detach", str(wt), "HEAD"],
            capture_output=True,
            text=True,
        )
        if add.returncode != 0:
            return False, "worktree_add_failed:" + add.stderr.strip()
        added = True

        gate_path = wt / GATE_REL
        gate = _load(gate_path)
        gate["owner_approval_ref"] = None
        gate["network_calls_authorized"] = False
        gate_path.write_text(
            json.dumps(gate, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        proc = subprocess.run(
            [sys.executable, str(wt / FROZEN_VERIFIER_REL)],
            cwd=str(wt),
            capture_output=True,
            text=True,
        )
        output = proc.stdout
        if proc.stderr:
            output += ("\n" if output else "") + proc.stderr
        return proc.returncode == 0, output
    finally:
        if added:
            subprocess.run(
                ["git", "-C", str(ROOT), "worktree", "remove", "--force", str(wt)],
                capture_output=True,
                text=True,
            )
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"check={name}:{'PASS' if ok else 'FAIL'}" + (f" :: {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    frozen_ok, frozen_output = _run_frozen_verifier()
    check("01_frozen_semantic_verifier", frozen_ok)
    if not frozen_ok:
        print("--- frozen verifier output ---")
        print(frozen_output)

    gate = _load(ROOT / GATE_REL)
    approval_present = bool(gate.get("owner_approval_ref"))
    network_authorized = gate.get("network_calls_authorized") is True
    authority_pair_ok = approval_present == network_authorized
    check(
        "02_calibration_authority_pair_coherent",
        authority_pair_ok,
        f"approval_present={approval_present} network_authorized={network_authorized}",
    )

    preflight = evaluate_jar15_calibration_preflight(ROOT)
    open_gates = _open_human_gates(gate)
    expected_decision = "NO_GO" if open_gates else "READY_TO_CALIBRATE"
    live_ok = (
        preflight.decision == expected_decision
        and set(preflight.blockers) == open_gates
    )
    check(
        "03_live_preflight_state_coherent",
        live_ok,
        f"expected={expected_decision} actual={preflight.decision} "
        f"open={sorted(open_gates)} blockers={sorted(preflight.blockers)}",
    )

    holdout = _load(ROOT / HOLDOUT_REL)
    analysis = _load(ROOT / ANALYSIS_REL)
    active = _load(ROOT / ACTIVE_REL)
    protocol_ref = gate.get("active_protocol_ref")
    protocol = _load(ROOT / protocol_ref) if isinstance(protocol_ref, str) else {}
    later_stages_closed = (
        holdout.get("network_calls_authorized") is False
        and analysis.get("network_calls_authorized") is False
        and active.get("network_calls_authorized") is False
        and protocol.get("network_calls_authorized") is False
    )
    check("04_later_stage_network_authority_closed", later_stages_closed)

    retries_closed = (
        gate.get("sdk_retries_allowed") is False
        and holdout.get("sdk_retries_allowed") is False
    )
    check("05_sdk_retries_remain_disabled", retries_closed)

    actual_pin = jar15_calibration_manifest_sha256(ROOT)
    pin_ok = gate.get("calibration_manifest_sha256") == actual_pin
    check(
        "06_frozen_manifest_pin_unchanged",
        pin_ok,
        f"gate={gate.get('calibration_manifest_sha256')} actual={actual_pin}",
    )

    if failures:
        print(f"verdict=FAIL failed={len(failures)}/6:" + "|".join(failures))
        return 1
    print("verdict=PASS checks=6/6")
    print("PASS: frozen semantic verifier + live Gate-B state are coherent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
