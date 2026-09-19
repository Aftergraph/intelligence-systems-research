#!/usr/bin/env python3
"""Regenerate the content-addressed INDEX.md for the JAR-EXP-0015 cross-repo
TypeSafe evidence package.

Runnable from any directory: every path is resolved relative to this file, never
to the current working directory. INDEX.md is excluded from its own hash
manifest (it embeds the others); this generator is included, and it never reads
INDEX.md, so the result is a stable fixed point rather than a hash cycle.

If a pinned foreign working copy is absent it is recorded as MISSING rather than
silently dropped, so a validator can tell the difference between "not reviewed"
and "not present on this machine".
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent      # evidence/typesafe-cross-repo
ROOT = HERE.parents[1]                      # the JAR-EXP-0015 repo root
GATE = ROOT / "data" / "jar_exp_0015_calibration_gate_v01.json"

FOREIGN = [
    ("war-room canonical main",
     "C:/Users/empir/workspace/war-room-audit-20260916",
     "EGAC consumer (documents the gap)"),
    ("war-room OER p0 fail-close",
     "C:/Users/empir/workspace/war-room-oer-p0",
     "EGAC consumer (halts; precondition source)"),
    ("war-room OER projection",
     "C:/Users/empir/workspace/war-room-oer-projection",
     "surface recon only"),
    ("war-room bridge (APPLIED, LOCAL UNMERGED)",
     "C:/Users/empir/workspace/war-room-typesafe-bridge",
     "bridge implementation + TSB 5/5"),
    ("Fihim typesafe layer",
     "C:/Users/empir/fihim-typesafe-wt",
     "real emitter, read-only"),
]

ROLES = {
    "war-room-typesafe-bridge.js":
        "REVIEWED artifact: TypeSafe->EGAC tier_1 bridge (invariants I1..I5)",
    "verify_typesafe_bridge.mjs":
        "Proof 1 harness: bridge invariants vs real EGAC (main + OER)",
    "verification-output.txt":
        "Captured harness output (8/8 PASS)",
    "hermes-pin-projection-smoke.mjs":
        "Proof 3 canary: pin-smoke + projection-smoke (read-only, zero-network)",
    "canary-output.txt":
        "Captured canary output (2/2 PASS)",
    "ADR-TYPESAFE-ADVISORY-BOUNDARY.md":
        "Architecture rule: advisory-only, tier_1-bound, OER precondition",
    "HERMES-CANARY-PROPOSAL.md":
        "Proposed additive Hermes cron job (not applied)",
    "FIHIM-COVERAGE-REVIEW.md":
        "Emitter-side review: suite passes, no change warranted",
    "verify_crossrepo_end_to_end.mjs":
        "Proof 2 e2e: REAL Fihim -> applied bridge -> both EGACs; fetch stubbed",
    "crossrepo-e2e-output.txt":
        "Captured e2e output (8/8 PASS)",
    "validate_hermes_stanza.mjs":
        "Proof 4: stanza conformance vs REAL cron spec (simulated merge only)",
    "hermes-stanza-validation-output.txt":
        "Captured stanza validation output (6/6 PASS)",
    "hermes-canary-job.proposed.json":
        "Exact proposed additive cron stanza (machine-validated; not applied)",
    "CROSS-REPO-ALIGNMENT-REPORT.md":
        "The alignment proof across all repos (24 checks, 0 failures)",
    "verify_gate_plumbing_dry_run.py":
        "Proof 5 gate-plumbing dry-run: REAL 0015 preflight, NO_GO->READY with only the 3 human gates",
    "gate-dry-run-output.txt":
        "Captured dry-run output (15/15 PASS; synthetic records are temp-only, deleted on exit)",
    "generate_index.py":
        "This generator, so the INDEX is reproducible and itself content-addressed",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def git(cwd: str, *args: str) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", cwd, *args],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as exc:
        return "<git error: %s>" % exc
    if r.returncode != 0:
        return "<git exit %d>" % r.returncode
    return r.stdout.strip()


def main() -> int:
    if not GATE.exists():
        print("FATAL: calibration gate not found: %s" % GATE, file=sys.stderr)
        return 1
    pin = json.loads(GATE.read_text(encoding="utf-8"))["calibration_manifest_sha256"]

    rows = []
    for label, path, note in FOREIGN:
        if not Path(path).exists():
            rows.append((label, path, "MISSING", "MISSING", "MISSING", note))
            continue
        branch = git(path, "rev-parse", "--abbrev-ref", "HEAD")
        sha = git(path, "rev-parse", "HEAD")
        dirty = git(path, "status", "--porcelain")
        if dirty.startswith("<"):
            clean = "UNKNOWN"
        else:
            clean = "clean" if dirty == "" else "DIRTY (%d)" % len(dirty.splitlines())
        rows.append((label, path, branch, sha, clean, note))

    files = sorted(p for p in HERE.iterdir() if p.is_file() and p.name != "INDEX.md")
    h = {p.name: sha256(p) for p in files}

    bridge_head = ""
    for label, _path, _branch, sha, _clean, _note in rows:
        if "APPLIED" in label and not sha.startswith("<") and len(sha) >= 7:
            bridge_head = sha[:7]
    reviewed_bridge_hash = h.get("war-room-typesafe-bridge.js", "?")

    L = []
    A = L.append

    A("# Evidence package INDEX - JAR-EXP-0015 cross-repo TypeSafe advisory boundary")
    A("")
    A("- **Experiment:** JAR-EXP-0015 (parent JAR-EXP-0014)")
    A("- **Date:** 2026-09-20 (initial package 2026-09-19)")
    A("- **Status:** Proven by execution. One LOCAL unmerged implementation (the war-room")
    A("  bridge); no foreign tree merged or pushed. JAR-EXP-0015 remains **NO_GO**.")
    A("- **Frozen 0015 calibration manifest pin:** `%s`" % pin)
    A("")
    A("Every artifact is content-addressed by SHA-256 and bound to the exact foreign")
    A("working-copy commits listed below, so a validator can confirm byte-for-byte what was")
    A("reviewed and re-run every proof. Start with `CROSS-REPO-ALIGNMENT-REPORT.md`.")
    A("")

    A("## Proof ledger (all outputs captured and hashed in this directory)")
    A("")
    A("| # | Proof | Script | Result |")
    A("|---|-------|--------|--------|")
    A("| 1 | Bridge invariants I1..I5 + fail-closed, vs real EGAC (main + OER) | `verify_typesafe_bridge.mjs` | 8/8 PASS |")
    A("| 2 | Emitter honesty + applied==reviewed + real-bytes gap + enforced fetch guard | `verify_crossrepo_end_to_end.mjs` | 8/8 PASS |")
    A("| 3 | Hermes canary: 0015 pin reproduces, NO_GO preserved, OER fail-close holds | `hermes-pin-projection-smoke.mjs` | 2/2 PASS |")
    A("| 4 | Cron stanza conformance vs the REAL spec (key shape, id, skills, global_safety) | `validate_hermes_stanza.mjs` | 6/6 PASS |")
    A("| 5 | Gate-plumbing rehearsal: REAL 0015 preflight reaches READY_TO_CALIBRATE with only the 3 human gates; one-gate-at-a-time negative controls | `verify_gate_plumbing_dry_run.py` | 15/15 PASS |")
    A("")
    A("**39 checks across 5 proofs, 0 failures, 0 network calls, 0 foreign-tree writes** (the")
    A("one deliberate persistent write is the LOCAL unmerged bridge commit below; proof 5 writes")
    A("only to a throwaway temp dir, deleted on exit). Proofs 1-4 are the cross-repo TypeSafe")
    A("alignment (24 checks, the scope of `CROSS-REPO-ALIGNMENT-REPORT.md`); proof 5 is the")
    A("gate-plumbing rehearsal against the real preflight (15 checks). Re-running proofs 1, 3")
    A("and 5 after every edit produced byte-identical output to the captured records")
    A("(`HARNESS_IDENTICAL`, `CANARY_IDENTICAL`, `DRYRUN_IDENTICAL`).")
    A("")

    A("## Foreign working copies (read-only unless noted)")
    A("")
    A("| Repo | Path | Branch | HEAD | Tree | Role |")
    A("|------|------|--------|------|------|------|")
    for label, path, branch, sha, clean, note in rows:
        short = sha[:12] if len(sha) >= 12 else sha
        A("| %s | `%s` | `%s` | `%s` | %s | %s |" % (label, path, branch, short, clean, note))
    A("")
    A("The single write in this whole package is the **LOCAL, UNMERGED, UNPUSHED** bridge")
    A("commit `%s` on `feat/typesafe-egac-bridge`, cut from OER `4a545fb` so it carries the" % bridge_head)
    A("`c076ccf` fail-close precondition. Its `packages/egac/src/typesafeBridge.js` is asserted")
    A("byte-identical to the reviewed artifact here (`%s...`) by proof 2. Merging it, or" % reviewed_bridge_hash[:12])
    A("editing the Hermes cron spec, are owner actions.")
    A("")

    A("## Artifact manifest (SHA-256)")
    A("")
    A("| File | SHA-256 | Role |")
    A("|------|---------|------|")
    for p in files:
        A("| `%s` | `%s` | %s |" % (p.name, h[p.name], ROLES.get(p.name, "")))
    A("")
    A("`INDEX.md` is excluded (it embeds the others' hashes). `generate_index.py` is included")
    A("and never reads `INDEX.md`, so this is a stable fixed point, not a hash cycle.")
    A("")

    A("## Reproduction")
    A("")
    A("```sh")
    A("# 1. Bridge invariants against the real foreign EGAC (read-only, zero-network):")
    A("node evidence/typesafe-cross-repo/verify_typesafe_bridge.mjs")
    A("")
    A("# 2. End-to-end alignment: REAL Fihim -> applied bridge -> both EGACs (fetch stubbed):")
    A("node --experimental-strip-types evidence/typesafe-cross-repo/verify_crossrepo_end_to_end.mjs")
    A("")
    A("# 3. Hermes canary (pin-smoke + projection-smoke, read-only, zero-network):")
    A("node evidence/typesafe-cross-repo/hermes-pin-projection-smoke.mjs")
    A("")
    A("# 4. Cron stanza conformance (simulated merge only; real spec untouched):")
    A("node evidence/typesafe-cross-repo/validate_hermes_stanza.mjs")
    A("")
    A("# 5. Gate-plumbing dry-run (REAL preflight; synthetic records are temp-only, deleted):")
    A("python evidence/typesafe-cross-repo/verify_gate_plumbing_dry_run.py")
    A("")
    A("# 6. Regenerate this INDEX (cwd-independent; hashes every artifact above):")
    A("python evidence/typesafe-cross-repo/generate_index.py")
    A("")
    A("# 7. Fihim emitter suite (no change; observed pass):")
    A("npm --prefix ~/fihim-typesafe-wt run test:typesafe-intelligence")
    A("")
    A("# 8. Applied bridge suite + OER boundary regression (in the bridge worktree):")
    A("node --test ~/workspace/war-room-typesafe-bridge/packages/egac/tests/typesafe-bridge.test.js")
    A("node --test ~/workspace/war-room-typesafe-bridge/tests/oer-p0-boundary.test.js")
    A("")
    A("# 9. Frozen 0015 record still green + NO_GO:")
    A("python scripts/verify_jar_exp_0015_semantic_review.py")
    A("```")
    A("")
    A("Each proof SKIPs (exit 2) rather than fabricating a result if a pinned working copy is")
    A("absent. Proof 2 installs a throwing `globalThis.fetch` stub **before** any import, so")
    A("zero-network is enforced by construction, not promised.")
    A("")

    A("## Safety / non-goals")
    A("")
    A("- **No signed `dist/` bundle is regenerated.** The modified `dist/*.zip` and")
    A("  `SUBMISSION_MANIFEST.json` in the working tree are left untouched; this package is")
    A("  0015-scoped only.")
    A("- **No foreign tree is merged or pushed.** War-room (do-not-merge), Fihim, and the")
    A("  Hermes `ci-local`-gated convergence branch (4 dirty `renos/` files preserved) are")
    A("  read-only. The one exception is the deliberate LOCAL unmerged bridge branch above.")
    A("- **JAR-EXP-0015 stays NO_GO.** No live TypeSafe/jev provider call is authorized; the")
    A("  three human gates (semantic review, owner approval, network authorization) remain")
    A("  closed. This package records authority; it never creates it.")
    A("")

    out = HERE / "INDEX.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("INDEX.md regenerated: %d artifacts hashed, pin=%s" % (len(files), pin))
    print("wrote %s (%d bytes)" % (out, out.stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())