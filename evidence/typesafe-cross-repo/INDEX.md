# Evidence package INDEX - JAR-EXP-0015 cross-repo TypeSafe advisory boundary

- **Experiment:** JAR-EXP-0015 (parent JAR-EXP-0014)
- **Date:** 2026-09-20 (initial package 2026-09-19)
- **Status:** Proven by execution. One LOCAL unmerged implementation (the war-room
  bridge); no foreign tree merged or pushed. JAR-EXP-0015 remains **NO_GO**.
- **Frozen 0015 calibration manifest pin:** `dc5d7a94f333908abf09aebe1ca1dbf08f965e604eb2919d0b7a9ca70e149762`

Every artifact is content-addressed by SHA-256 and bound to the exact foreign
working-copy commits listed below, so a validator can confirm byte-for-byte what was
reviewed and re-run every proof. Start with `CROSS-REPO-ALIGNMENT-REPORT.md`.

## Proof ledger (all outputs captured and hashed in this directory)

| # | Proof | Script | Result |
|---|-------|--------|--------|
| 1 | Bridge invariants I1..I5 + fail-closed, vs real EGAC (main + OER) | `verify_typesafe_bridge.mjs` | 8/8 PASS |
| 2 | Emitter honesty + applied==reviewed + real-bytes gap + enforced fetch guard | `verify_crossrepo_end_to_end.mjs` | 8/8 PASS |
| 3 | Hermes canary: 0015 pin reproduces, NO_GO preserved, OER fail-close holds | `hermes-pin-projection-smoke.mjs` | 2/2 PASS |
| 4 | Cron stanza conformance vs the REAL spec (key shape, id, skills, global_safety) | `validate_hermes_stanza.mjs` | 6/6 PASS |
| 5 | Gate-plumbing rehearsal: REAL 0015 preflight reaches READY_TO_CALIBRATE with only the 3 human gates; one-gate-at-a-time negative controls | `verify_gate_plumbing_dry_run.py` | 15/15 PASS |

**39 checks across 5 proofs, 0 failures, 0 network calls, 0 foreign-tree writes** (the
one deliberate persistent write is the LOCAL unmerged bridge commit below; proof 5 writes
only to a throwaway temp dir, deleted on exit). Proofs 1-4 are the cross-repo TypeSafe
alignment (24 checks, the scope of `CROSS-REPO-ALIGNMENT-REPORT.md`); proof 5 is the
gate-plumbing rehearsal against the real preflight (15 checks). Re-running proofs 1, 3
and 5 after every edit produced byte-identical output to the captured records
(`HARNESS_IDENTICAL`, `CANARY_IDENTICAL`, `DRYRUN_IDENTICAL`).

## Foreign working copies (read-only unless noted)

| Repo | Path | Branch | HEAD | Tree | Role |
|------|------|--------|------|------|------|
| war-room canonical main | `C:/Users/empir/workspace/war-room-audit-20260916` | `main` | `0313ad91ce96` | clean | EGAC consumer (documents the gap) |
| war-room OER p0 fail-close | `C:/Users/empir/workspace/war-room-oer-p0` | `fix/oer-p0-authority-boundary` | `4a545fb808d1` | clean | EGAC consumer (halts; precondition source) |
| war-room OER projection | `C:/Users/empir/workspace/war-room-oer-projection` | `feat/oer-war-room-projection` | `13d9ed4c0873` | clean | surface recon only |
| war-room bridge (APPLIED, LOCAL UNMERGED) | `C:/Users/empir/workspace/war-room-typesafe-bridge` | `feat/typesafe-egac-bridge` | `6be6d80f6c77` | clean | bridge implementation + TSB 5/5 |
| Fihim typesafe layer | `C:/Users/empir/fihim-typesafe-wt` | `feat/typesafe-intelligence-layer` | `34780e8f250c` | clean | real emitter, read-only |

The single write in this whole package is the **LOCAL, UNMERGED, UNPUSHED** bridge
commit `6be6d80` on `feat/typesafe-egac-bridge`, cut from OER `4a545fb` so it carries the
`c076ccf` fail-close precondition. Its `packages/egac/src/typesafeBridge.js` is asserted
byte-identical to the reviewed artifact here (`efb6348bcbac...`) by proof 2. Merging it, or
editing the Hermes cron spec, are owner actions.

## Artifact manifest (SHA-256)

| File | SHA-256 | Role |
|------|---------|------|
| `ADR-TYPESAFE-ADVISORY-BOUNDARY.md` | `734f61a055e0a027da770d8c5571cf545b91cefa3d7f7dbc458cb0dd1273b464` | Architecture rule: advisory-only, tier_1-bound, OER precondition |
| `canary-output.txt` | `ebd814b7f39bac7c08cc4f27f9b373fd6a0430f46a8719b51fad3a7ee1757210` | Captured canary output (2/2 PASS) |
| `CROSS-REPO-ALIGNMENT-REPORT.md` | `9638968bfadc04702f63bebbce6668a1d0220162ab561a43912c00fc0418b1a7` | The alignment proof across all repos (24 checks, 0 failures) |
| `crossrepo-e2e-output.txt` | `f6a19212020d103be0d70f72b5599be21255a7005921f81efc93afd468472fb3` | Captured e2e output (8/8 PASS) |
| `FIHIM-COVERAGE-REVIEW.md` | `77125ed9fa9b5c817329ad6f9de9ebc87a1c6c7b04be5411d6afb1f5f13e9e93` | Emitter-side review: suite passes, no change warranted |
| `gate-dry-run-output.txt` | `94780ad6f3edf0026836ceafc663f7f48a90dcaad41014b414c292ceda86064e` | Captured dry-run output (15/15 PASS; synthetic records are temp-only, deleted on exit) |
| `generate_index.py` | `2d51c09d350154440320196bc9c64df8d1c804d60d011b1edf00adbde52bc4b2` | This generator, so the INDEX is reproducible and itself content-addressed |
| `hermes-canary-job.proposed.json` | `5068607473e8ee20ea3d68092f59e50c7031e6589b9b9b172b072811808d2045` | Exact proposed additive cron stanza (machine-validated; not applied) |
| `HERMES-CANARY-PROPOSAL.md` | `42c0fbe2bfca67248ae1dcf658a665b86c8d5a2944a2c94049e81e9eb5e72f2e` | Proposed additive Hermes cron job (not applied) |
| `hermes-pin-projection-smoke.mjs` | `ec4f8c6a5b4cb74238984d6c14c93f01568da04f415bb1eb0b2113b82a6fe36f` | Proof 3 canary: pin-smoke + projection-smoke (read-only, zero-network) |
| `hermes-stanza-validation-output.txt` | `51bfb2df2b9cbe0c0e4aa817d61201f5f18abaa854aadf4f38cc80446095e577` | Captured stanza validation output (6/6 PASS) |
| `validate_hermes_stanza.mjs` | `0e312090de8a24116554f2cdb6755175e237f79eea825e4e09c5336a4612f12f` | Proof 4: stanza conformance vs REAL cron spec (simulated merge only) |
| `verification-output.txt` | `9af0928b84c47c55400efa92bff8d8221f70eccdd8895e9bd236a1e28e34bc82` | Captured harness output (8/8 PASS) |
| `verify_crossrepo_end_to_end.mjs` | `a5ba92dc28aba4509281f02ff01a0d774465e3ee4322e908abc2ef96ac19d1e2` | Proof 2 e2e: REAL Fihim -> applied bridge -> both EGACs; fetch stubbed |
| `verify_gate_plumbing_dry_run.py` | `67c834360a25ae5eb6d7630df466baaff8ed6e31513b2d599471c0046a5fe834` | Proof 5 gate-plumbing dry-run: REAL 0015 preflight, NO_GO->READY with only the 3 human gates |
| `verify_typesafe_bridge.mjs` | `f45b67249591b184128bd246135a119e3557bc257e67f065abb6cb881a0b1bc4` | Proof 1 harness: bridge invariants vs real EGAC (main + OER) |
| `war-room-typesafe-bridge.js` | `efb6348bcbacc84eedae55edced5ea64e85fc6faf5d92f498b86f1afc36ff4f7` | REVIEWED artifact: TypeSafe->EGAC tier_1 bridge (invariants I1..I5) |

`INDEX.md` is excluded (it embeds the others' hashes). `generate_index.py` is included
and never reads `INDEX.md`, so this is a stable fixed point, not a hash cycle.

## Reproduction

```sh
# 1. Bridge invariants against the real foreign EGAC (read-only, zero-network):
node evidence/typesafe-cross-repo/verify_typesafe_bridge.mjs

# 2. End-to-end alignment: REAL Fihim -> applied bridge -> both EGACs (fetch stubbed):
node --experimental-strip-types evidence/typesafe-cross-repo/verify_crossrepo_end_to_end.mjs

# 3. Hermes canary (pin-smoke + projection-smoke, read-only, zero-network):
node evidence/typesafe-cross-repo/hermes-pin-projection-smoke.mjs

# 4. Cron stanza conformance (simulated merge only; real spec untouched):
node evidence/typesafe-cross-repo/validate_hermes_stanza.mjs

# 5. Gate-plumbing dry-run (REAL preflight; synthetic records are temp-only, deleted):
python evidence/typesafe-cross-repo/verify_gate_plumbing_dry_run.py

# 6. Regenerate this INDEX (cwd-independent; hashes every artifact above):
python evidence/typesafe-cross-repo/generate_index.py

# 7. Fihim emitter suite (no change; observed pass):
npm --prefix ~/fihim-typesafe-wt run test:typesafe-intelligence

# 8. Applied bridge suite + OER boundary regression (in the bridge worktree):
node --test ~/workspace/war-room-typesafe-bridge/packages/egac/tests/typesafe-bridge.test.js
node --test ~/workspace/war-room-typesafe-bridge/tests/oer-p0-boundary.test.js

# 9. Frozen 0015 record still green + NO_GO:
python scripts/verify_jar_exp_0015_semantic_review.py
```

Each proof SKIPs (exit 2) rather than fabricating a result if a pinned working copy is
absent. Proof 2 installs a throwing `globalThis.fetch` stub **before** any import, so
zero-network is enforced by construction, not promised.

## Safety / non-goals

- **No signed `dist/` bundle is regenerated.** The modified `dist/*.zip` and
  `SUBMISSION_MANIFEST.json` in the working tree are left untouched; this package is
  0015-scoped only.
- **No foreign tree is merged or pushed.** War-room (do-not-merge), Fihim, and the
  Hermes `ci-local`-gated convergence branch (4 dirty `renos/` files preserved) are
  read-only. The one exception is the deliberate LOCAL unmerged bridge branch above.
- **JAR-EXP-0015 stays NO_GO.** No live TypeSafe/jev provider call is authorized; the
  three human gates (semantic review, owner approval, network authorization) remain
  closed. This package records authority; it never creates it.

