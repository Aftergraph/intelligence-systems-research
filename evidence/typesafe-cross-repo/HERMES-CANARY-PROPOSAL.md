# Hermes canary proposal: periodic pin-smoke + projection-smoke

- **Status:** Proposed additive job. **Not applied** to the foreign cron spec.
- **Date:** 2026-09-19
- **Target:** `hermes/cron/rendetalje-cron-spec.json` (Rendetalje workspace, Hermes)
- **Script:** `hermes-pin-projection-smoke.mjs` (this evidence dir; drop into Hermes'
  `nora/model-routing` script directory unchanged — it is self-contained).

## What it guards

Three regressions that would silently invalidate the JAR-EXP-0015 freeze and the
TypeSafe advisory boundary:

1. **Pin drift.** The frozen 0015 calibration manifest must still reproduce the gate pin
   `dc5d7a94f333908abf09aebe1ca1dbf08f965e604eb2919d0b7a9ca70e149762`. Any edit to a
   manifest-tracked file after pinning breaks this — the canary catches it.
2. **Silent approval/semantic-review fabrication.** Preflight must remain `NO_GO` on the
   three human gates. If a record ever appears that flips it to `GO` without a real
   owner action, the canary fails. This is the experiment's central honesty guarantee,
   watched on a schedule.
3. **OER fail-close regression.** A lone `tier_1` model judgment and a `tier_0`
   self-assertion must never reach `AUTONOMOUS_EXECUTION`; `authority` must stay `NONE`.
   Mirrors war-room `tests/oer-p0-boundary.test.js` OER-004/005, but self-contained and
   read-only (it re-asserts the invariant; it does not run the foreign suite).

## Safety posture

The script is **read-only and zero-network** and inherits the cron spec's
`global_safety` (no external actions, no calendar mutations, no customer/invoice
messages, approval package required). It only inspects local working copies and the
frozen 0015 record. On any failed invariant it exits non-zero so the cron brief flags it.
Observed output (`canary-output.txt`):

```
PASS  pin_smoke_0015_manifest_and_nogo
PASS  projection_smoke_oer_fail_close
---
canary_checks=2 failures=0
external_actions_performed=0 network_calls=0 calendar_mutations=0
verdict=PASS
```

## Exact stanza to add (owner applies; append to `jobs[]`)

```json
{
  "id": "rendetalje-typesafe-canary",
  "schedule_hint": "Daily around 07:30 Europe/Copenhagen (after the ops brief)",
  "skills": ["nora-model-routing", "protected-action-gate", "approval-package-bundler"],
  "prompt": "Run the read-only TypeSafe/JAR-EXP-0015 canary (hermes-pin-projection-smoke.mjs). Report pin stability, NO_GO preservation, and OER fail-close status. Prepare a brief only; do not send messages, change calendars, or authorize anything.",
  "deliverable": "Canary brief: pin-smoke + projection-smoke pass/fail, zero-network"
}
```

It follows the existing jobs' shape exactly (id / schedule_hint / skills / prompt /
deliverable) and reuses the same guardrail skills (`protected-action-gate`,
`approval-package-bundler`).

## Why proposed, not applied

The Hermes parent branch (`fix/ci-vitest-baseline-convergence`) is the `ci-local`-gated
convergence branch and carries 4 dirty `renos/` files that must be preserved. The cron
spec itself is clean, but the standing constraint on these foreign trees is
do-not-merge / preserve-local-work, so the change is delivered here as a reviewable
proposal with the exact JSON, and application is left to the owner. Nothing in this
package writes to the Rendetalje workspace.