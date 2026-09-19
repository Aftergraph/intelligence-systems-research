# Cross-repo alignment report — TypeSafe/jev is advisory evidence, never authority

- **Date:** 2026-09-20
- **Experiment:** JAR-EXP-0015 (parent JAR-EXP-0014)
- **Frozen 0015 calibration manifest pin:** `dc5d7a94f333908abf09aebe1ca1dbf08f965e604eb2919d0b7a9ca70e149762`
- **Verdict:** **PROVEN BY EXECUTION** — 24 checks across 4 proof scripts, 0 failures,
  0 network calls, 0 foreign-tree mutations (one deliberate LOCAL unmerged commit).

This report is the answer to "bevis det — modstem mod alle repos": the single invariant
that JAR-EXP-0014/0015 are built to enforce on the research side — *a model opinion is
advisory inference and never authority* — is now shown to hold end-to-end across every
repository that touches a TypeSafe/jev judgment, by running the real modules, not by
asserting documents.

## The one invariant, four repos

```
Fihim (emitter)          war-room bridge (translation)        war-room EGAC (consumer)
34780e8                  6be6d80 (feat/typesafe-egac-bridge)  main 0313ad9 | OER 4a545fb
  SemanticJudgmentRecord  ->  tier_1 evidence item  ->  decide() -> autonomy recommendation
  "advisory inference     "tier_1 ONLY,                 advisoryOnly:true, authority:'NONE'
   only"                  advisoryOnly, no authority"    (OER) — NEVER executable authority
```

Hermes is the scheduled watchdog: it re-asserts the 0015 pin and the OER fail-close on a
cadence (canary 2/2 PASS), and its proposed cron stanza is validated conformant against
the real spec (6/6 PASS) without touching the `ci-local`-gated tree.

## Proof 1 — emitter honesty (Fihim `34780e8`)

The real `TYPE_SAFE_QUESTIONS` set omits the two authority keystones, and the real
`routeSemanticJudgment` can only return `DISPLAY`/`REVIEW`:

```
PASS  fihim_negative_keystones_absent      # no authorize_action, no verification_verdict
PASS  fihim_router_never_escalates_finding # exhaustive conf x consequence sweep -> {DISPLAY,REVIEW}
```

The second line is a *finding*, not a failure: `ESCALATE` exists in the type but is
unreachable from the current router. The bridge's `ESCALATE` handling is therefore
defense-in-depth for future emitters, not live behavior — and it is still proven inert
(Proof 3, `escalate_defense_in_depth_never_passes`).

## Proof 2 — the applied bridge is the reviewed bridge (byte-identical)

```
PASS  applied_bridge_byte_identical_to_reviewed   # sha256(applied) == sha256(reviewed efb6348b…)
PASS  real_fihim_records_bridge_clean             # REAL toSemanticJudgment output -> tier_1, advisory, lineage copied
```

The bridge landed for real on a fresh local worktree cut from the OER fail-close commit:

| Repo | Path | Branch | HEAD | Tree |
|------|------|--------|------|------|
| war-room bridge (applied) | `C:/Users/empir/workspace/war-room-typesafe-bridge` | `feat/typesafe-egac-bridge` | `6be6d80` | clean |

Its own repo-convention suite passes **TSB 5/5**, and the existing OER boundary suite
passes **8/8** with no regression. Committed locally, **unmerged, unpushed**; all
pre-existing worktrees untouched.

## Proof 3 — the load-bearing gap, on real bytes (the whole point)

The *same* real Fihim `DISPLAY` record, bridged identically, meets opposite decisions
because of commit `c076ccf` ("fail close local authority boundaries"):

```
PASS  oer_egac_halts_on_real_bridge_output    # OER 4a545fb: HALT_AND_ESCALATE, authority:'NONE', advisoryOnly:true
PASS  main_egac_gap_on_real_bridge_output     # main 0313ad9: AUTONOMOUS_EXECUTION  <-- the documented gap
PASS  escalate_defense_in_depth_never_passes  # ESCALATE can never satisfy the gate or launder authority
PASS  zero_network_guard_held                 # globalThis.fetch stubbed to throw BEFORE any import
```

`c076ccf` inverts the cost-asymmetry threshold (`alpha = costFN/(costFP+costFN)` → 0.05),
demotes `AUTONOMOUS_EXECUTION` → `RECOMMEND_AUTOMATION`, and stamps every decision
`advisoryOnly:true` / `authority:'NONE'`. That is why the ADR binds the bridge to the OER
precondition as a **prohibited configuration** on canonical main, not a preference: wiring
the bridge into a non-OER war-room would convert advisory model output into an executable
autonomy signal. The harness proves both halves of that claim by execution.

## Proof 4 — Hermes watchdog + stanza conformance (no foreign write)

```
# canary (hermes-pin-projection-smoke.mjs):
PASS  pin_smoke_0015_manifest_and_nogo        # frozen manifest still reproduces dc5d7a94…; preflight still NO_GO
PASS  projection_smoke_oer_fail_close         # OER fail-close still holds

# stanza validator (validate_hermes_stanza.mjs, against the REAL cron spec):
PASS  stanza_key_shape_matches_existing_jobs
PASS  stanza_id_unique
PASS  stanza_skills_are_known_in_workspace_specs
PASS  simulated_merge_preserves_global_safety_and_top_level   # tree untouched; merge simulated only
```

The Hermes parent branch (`fix/ci-vitest-baseline-convergence`) is the `ci-local`-gated
convergence branch carrying 4 dirty `renos/` files that must be preserved; the stanza is
delivered as a reviewable proposal, application left to the owner.

## Regression: nothing drifted

Re-running the original harness and canary after all edits produced **byte-identical**
output to the committed records:

```
HARNESS_IDENTICAL
CANARY_IDENTICAL
```

## Alignment summary — modstem mod alle repos

| Repo | Role | Commit | Aligned? | How proven |
|------|------|--------|----------|------------|
| Fihim | emitter | `34780e8` | yes | negative keystones absent; router DISPLAY/REVIEW only |
| war-room bridge | translation | `6be6d80` (local, unmerged) | yes | byte-identical to reviewed; TSB 5/5; OER 8/8 no regression |
| war-room EGAC (OER) | consumer | `4a545fb` | yes | lone tier_1 → HALT, authority NONE |
| war-room EGAC (main) | consumer | `0313ad9` | gap documented | lone tier_1 → AUTONOMOUS_EXECUTION (the precondition) |
| Hermes | watchdog | cron spec (read-only) | yes | canary 2/2; stanza 6/6 conformant |
| JAR-EXP-0015 | governance | pin `dc5d7a94…` | yes | 38/38 verifier; NO_GO preserved; pin unmoved by evidence |

## What remains (the human gate — I will not fabricate it)

The experiment is complete and honest up to the boundary it is forbidden to cross. To flip
`NO_GO → GO` for live calibration, three independent human artifacts must appear, exactly
as JAR-EXP-0014's terminal records show:

1. A **semantic-review record** bound to pin `dc5d7a94…` (0014 analog: `PASS_WITH_FINDINGS`
   from an independent verifier on an isolated CI runner).
2. An **owner approval** (`approved:true`, `network_calls_authorized:true`, parity on
   `jev-1.13.0` / manifest / 1952 calls / $5.38 ceiling) — the `PENDING` template is the
   shape to sign.
3. **Network authorization** — the gate stays `network_calls_authorized:false` and
   `sdk_retries_allowed:false` until granted.

The ADR, the bridge, and the Hermes stanza are all *proposed*; the bridge is implemented on
a local unmerged branch for verification only. Applying it to a shared war-room, merging
`feat/typesafe-egac-bridge`, or editing the Hermes cron spec are owner actions. Nothing in
this package regenerates a signed `dist/` bundle.