#!/usr/bin/env python3
"""Gate-plumbing dry-run for JAR-EXP-0015 calibration authorization.

Purpose
-------
Exercise the REAL fail-closed preflight
(``experiments.system_one_acceleration.jar15_calibration_preflight
.evaluate_jar15_calibration_preflight``) against a faithful throwaway copy of
the working tree, to prove *mechanically* that the ONLY things standing between
the current NO_GO state and READY_TO_CALIBRATE are the human gates:

  1. a content-addressed semantic falsification review record,
  2. an explicit owner/calibration approval record,
  3. ``network_calls_authorized`` flipped to true on the calibration gate.

The baseline is ADAPTIVE. It asserts the preflight's blockers are exactly the
human gates that are still OPEN, whatever that set is, and that no blocker
outside the three human gates leaks. When this harness was authored all three
were open; the independent semantic review has since been closed by a real
isolated CI run (commit 1a2dc7f, run 35473954572), so the live baseline is now
{owner approval, network authorization}. The mechanism proved is unchanged and
is what matters: each gate is individually necessary (negative controls 08-10)
and all together they are sufficient (positive control 06). Adapting the
snapshot to the true open set never weakens the control -- a stale "all three
open" assertion would merely be false, not safer.

Safety contract
---------------
This script NEVER writes a real record into the repository. The synthetic review
and approval documents are constructed inside a throwaway temp directory, are
labelled ``DRY-RUN-TEMPLATE`` throughout, and are deleted on exit. Their sole
purpose is to demonstrate that a well-formed human-placed record satisfies the
preflight's field contract. No approval or semantic review is fabricated in any
persistent location, and the real gate's NO_GO state and manifest pin are
asserted untouched (checks 13-14).

Zero-network: this script makes no provider call and imports no SDK client. It
only reads frozen local JSON and runs a pure-function preflight. The manifest is
recomputed from disk (``content_manifest_sha256`` -> ``Path.read_bytes``), so a
byte-identical copy reproduces the pin without any git access.

Note on schema conformance
--------------------------
The templates below satisfy the LIVE 0015 preflight field contract. They are
deliberately NOT conformant to ``schemas/system-one-*-receipt.v0.1.json``, which
const ``experiment_id`` to ``JAR-EXP-0014`` and are frozen inside the 0014
manifests (``integrity.py``). Nothing in the 0015 path schema-validates a
human-placed 0015 record against those files, so the preflight's per-field checks
are the sole live contract for 0015. Surfacing this is part of the point.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from experiments.system_one_acceleration.jar15_calibration_preflight import (  # noqa: E402
    GATE_REF,
    evaluate_jar15_calibration_preflight,
)
from experiments.system_one_acceleration.jar15_integrity import (  # noqa: E402
    JAR15_CALIBRATION_INTEGRITY_PATHS,
    jar15_calibration_manifest_sha256,
)

# Top-level entries that hold every manifest path + every data file the preflight
# reads. A targeted copy of these is faithful and fast; .git / caches / the
# untracked live-benchmark dry-runs are irrelevant to the preflight and skipped.
COPY_DIRS = ("experiments", "data", "schemas", "scripts")
COPY_FILES = ("requirements-typesafe.txt",)
IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".mypy_cache", ".pytest_cache", "live_benchmark_dry_runs"
)

HUMAN_GATES = {
    "jar15_semantic_review_not_recorded",
    "jar15_approval_not_recorded",
    "jar15_network_calls_not_authorized",
}

TS = "2026-09-20T12:00:00+00:00"  # fixed -> deterministic output
REVIEW_REL = "data/jar_exp_0015_semantic_review_DRYRUN.json"
APPROVAL_REL = "data/jar_exp_0015_owner_approval_DRYRUN.json"


def open_human_gates(gate: dict) -> set[str]:
    """The subset of HUMAN_GATES still unsatisfied by ``gate``.

    Mirrors ``evaluate_jar15_calibration_preflight`` exactly: a falsy
    ``semantic_review_ref``/``owner_approval_ref`` yields the corresponding
    ``*_not_recorded`` blocker, and a ``network_calls_authorized`` that is not
    literally ``True`` yields ``jar15_network_calls_not_authorized``. Keeping
    this in lockstep is what lets the baseline assert "only the open human gates
    block" without hardcoding how many are open.
    """
    open_gates: set[str] = set()
    if not gate.get("semantic_review_ref"):
        open_gates.add("jar15_semantic_review_not_recorded")
    if not gate.get("owner_approval_ref"):
        open_gates.add("jar15_approval_not_recorded")
    if gate.get("network_calls_authorized") is not True:
        open_gates.add("jar15_network_calls_not_authorized")
    return open_gates


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

    tmp = Path(tempfile.mkdtemp(prefix="jar15-gate-dryrun-"))
    try:
        tree = tmp / "repo"
        tree.mkdir()
        for rel in COPY_DIRS:
            shutil.copytree(REPO_ROOT / rel, tree / rel, ignore=IGNORE)
        for rel in COPY_FILES:
            shutil.copy2(REPO_ROOT / rel, tree / rel)

        missing = [p for p in JAR15_CALIBRATION_INTEGRITY_PATHS if not (tree / p).exists()]
        check("00_all_manifest_paths_present_in_temp", not missing,
              "missing=" + ",".join(missing))

        # Manifest reproduces on the disk copy (proves faithfulness).
        pin_real = jar15_calibration_manifest_sha256(REPO_ROOT)
        pin_copy = jar15_calibration_manifest_sha256(tree)
        check("01_manifest_reproduces_on_copy", pin_real == pin_copy, f"pin={pin_copy}")

        gate_path = tree / GATE_REF
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        check("02_gate_pin_matches_manifest",
              gate.get("calibration_manifest_sha256") == pin_copy)

        requested_model = gate["requested_model"]
        max_calls = gate["max_provider_calls"]
        max_cost = gate["max_cost_usd"]

        # BASELINE: unpatched copy -> NO_GO with exactly the OPEN human gates.
        # ``gate`` is the inherited (unpatched) gate dict, so open_human_gates(gate)
        # is the true current open set; the preflight must block on precisely that
        # and on nothing outside HUMAN_GATES.
        base = evaluate_jar15_calibration_preflight(tree)
        baseline_open = open_human_gates(gate)
        check("03_baseline_no_go", base.decision == "NO_GO", f"decision={base.decision}")
        check("04_baseline_blockers_are_exactly_the_open_human_gates",
              set(base.blockers) == baseline_open and set(base.blockers) <= HUMAN_GATES,
              "open=" + "|".join(sorted(baseline_open))
              + " blockers=" + "|".join(sorted(base.blockers)))

        # Synthetic DRY-RUN records (temp only; obviously labelled; never real).
        review = {
            "schema_version": "aftergraph.system-one-semantic-review/0.1",
            "experiment_id": "JAR-EXP-0015",
            "verdict": "PASS_WITH_FINDINGS",
            "independent": True,
            "reviewer": "DRY-RUN-TEMPLATE-NOT-A-REAL-REVIEWER",
            "reviewer_kind": "independent_verifier",
            "reviewed_at": TS,
            "calibration_manifest_sha256": pin_copy,
            "falsification_attempts_considered": 38,
            "evidence_ref": "DRY-RUN: no real CI run; template only",
            "findings": [],
        }
        approval = {
            "schema_version": "aftergraph.system-one-calibration-approval/0.1",
            "experiment_id": "JAR-EXP-0015",
            "approved": True,
            "network_calls_authorized": True,
            "requested_typesafe_model": requested_model,
            "calibration_manifest_sha256": pin_copy,
            "max_provider_calls": max_calls,
            "max_cost_usd": max_cost,
            "approved_by": "DRY-RUN-TEMPLATE-NOT-A-REAL-OWNER",
            "approved_at": TS,
        }
        (tree / REVIEW_REL).write_text(json.dumps(review, indent=2), encoding="utf-8")
        (tree / APPROVAL_REL).write_text(json.dumps(approval, indent=2), encoding="utf-8")
        check("05_dryrun_records_written_to_temp_only",
              (tree / REVIEW_REL).exists() and (tree / APPROVAL_REL).exists())

        def write_gate(**overrides) -> None:
            g = dict(gate)
            g.update(overrides)
            gate_path.write_text(json.dumps(g, indent=2), encoding="utf-8")

        # POSITIVE: satisfy all three gates -> READY_TO_CALIBRATE, zero blockers.
        write_gate(semantic_review_ref=REVIEW_REL, owner_approval_ref=APPROVAL_REL,
                   network_calls_authorized=True)
        pos = evaluate_jar15_calibration_preflight(tree)
        check("06_all_three_gates_satisfied_reaches_ready",
              pos.decision == "READY_TO_CALIBRATE",
              f"decision={pos.decision} blockers={'|'.join(sorted(pos.blockers))}")
        check("07_ready_has_zero_blockers", pos.blockers == (),
              f"blockers={'|'.join(sorted(pos.blockers))}")

        # NEGATIVE CONTROLS: revert exactly one gate -> NO_GO with only that blocker.
        write_gate(semantic_review_ref=None, owner_approval_ref=APPROVAL_REL,
                   network_calls_authorized=True)
        nc = evaluate_jar15_calibration_preflight(tree)
        check("08_revert_semantic_review_alone_blocks",
              nc.decision == "NO_GO"
              and set(nc.blockers) == {"jar15_semantic_review_not_recorded"},
              f"blockers={'|'.join(sorted(nc.blockers))}")

        write_gate(semantic_review_ref=REVIEW_REL, owner_approval_ref=None,
                   network_calls_authorized=True)
        nc = evaluate_jar15_calibration_preflight(tree)
        check("09_revert_owner_approval_alone_blocks",
              nc.decision == "NO_GO"
              and set(nc.blockers) == {"jar15_approval_not_recorded"},
              f"blockers={'|'.join(sorted(nc.blockers))}")

        write_gate(semantic_review_ref=REVIEW_REL, owner_approval_ref=APPROVAL_REL,
                   network_calls_authorized=False)
        nc = evaluate_jar15_calibration_preflight(tree)
        check("10_revert_network_alone_blocks",
              nc.decision == "NO_GO"
              and set(nc.blockers) == {"jar15_network_calls_not_authorized"},
              f"blockers={'|'.join(sorted(nc.blockers))}")

        # MANIFEST STABILITY: gate + records are outside the 30-path manifest, so
        # every patch above never moved the pin.
        pin_after = jar15_calibration_manifest_sha256(tree)
        check("11_pin_unchanged_after_gate_and_record_patches", pin_after == pin_copy,
              f"pin={pin_after}")

        # REAL TREE UNTOUCHED: the live repo still NO_GO, blocked on exactly the
        # open human gates (read fresh from the real gate file, not the patched
        # temp copy), with the pin intact (check 13).
        real_gate = json.loads((REPO_ROOT / GATE_REF).read_text(encoding="utf-8"))
        real_open = open_human_gates(real_gate)
        real = evaluate_jar15_calibration_preflight(REPO_ROOT)
        check("12_real_tree_still_no_go",
              real.decision == "NO_GO"
              and set(real.blockers) == real_open
              and set(real.blockers) <= HUMAN_GATES,
              f"decision={real.decision} open={'|'.join(sorted(real_open))}"
              f" blockers={'|'.join(sorted(real.blockers))}")
        check("13_real_pin_unchanged",
              jar15_calibration_manifest_sha256(REPO_ROOT) == pin_real)

        # Emit the templates the human can cite (clearly synthetic).
        print("---TEMPLATE semantic-review record (satisfies live 0015 preflight)---")
        print(json.dumps(review, indent=2))
        print("---TEMPLATE owner-approval record (satisfies live 0015 preflight)---")
        print(json.dumps(approval, indent=2))
        print("---TEMPLATE the three gate edits that open the gate---")
        print(json.dumps({
            "semantic_review_ref": REVIEW_REL,
            "owner_approval_ref": APPROVAL_REL,
            "network_calls_authorized": True,
        }, indent=2))
        print("---NOTE schema conformance---")
        print("These templates satisfy jar15_calibration_preflight's per-field")
        print("contract. They are NOT conformant to the 0014-const")
        print("schemas/system-one-*-receipt.v0.1.json (frozen in the 0014")
        print("manifests, unused for 0015). For formal 0015 schema conformance the")
        print("owner should fork those two schemas as new 0015 files (outside the")
        print("30-path manifest, so pin dc5d7a94 is unaffected).")
        print("---NOTE current live status---")
        print("Gate A (the independent semantic review) is already closed for real")
        print("(commit 1a2dc7f, isolated CI run 35473954572), so the live preflight")
        print("baseline is the two outstanding human gates (owner approval + network")
        print("authorization). The three templates above remain the full mechanism,")
        print("shown for completeness and to drive the one-gate-at-a-time negative")
        print("controls (08-10), which are independent of how many gates are open.")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        check("14_temp_directory_removed", not tmp.exists())

    print()
    total = 15
    if failures:
        print(f"verdict=FAIL failed={len(failures)}/{total}:{'|'.join(failures)}")
        return 1
    print(f"verdict=PASS checks={total}/{total}")
    print("PASS: JAR-EXP-0015 gate-plumbing dry-run vs real preflight")
    print("falsification_attempts=15")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())