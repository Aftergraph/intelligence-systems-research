# ADR: TypeSafe/jev output is bound to EGAC tier_1 and never crosses the authority boundary

- **Status:** Proposed — awaiting owner ratification. Not applied to any foreign tree.
- **Date:** 2026-09-19
- **Scope:** JAR-EXP-0015 cross-repo evidence package. Governs how Fihim's TypeSafe
  semantic judgments may be consumed by war-room's Evidence-Gated Autonomy Controller
  (EGAC).
- **Deciders:** Aftergraph research (author: deterministic build agent; ratification:
  human owner — this ADR records a proposed rule, it does not enact one).

## Context

Three repositories meet at one seam, and today nothing bridges them:

1. **Fihim** (`feat/typesafe-intelligence-layer`, HEAD `34780e8`) emits
   `SemanticJudgmentRecord` objects from the TypeSafe `jev` model. Their own contract is
   explicit — `src/domain/semanticJudgment.ts:22-24`:

   > TypeSafe judgments are advisory inference only. They never authorize, execute, or
   > verify consequential actions.

   The question set enforces it: `src/integrations/typesafe/questions.ts:6-7` carries
   only narrow semantic questions and deliberately omits `authorize_action` and
   `verification_verdict`. The routing function (`semanticJudgment.ts:25-29`) can only
   return `DISPLAY | REVIEW | ESCALATE` — never an authority verdict.

2. **War-room** (`Aftergraph/war-room.git`) has exactly one slot whose epistemic
   strength matches a model opinion: EGAC `tier_1 / model_judgment`
   (`packages/egac/src/index.js:24`, sensitivity 0.45 / specificity 0.90). It is consumed
   by `EvidenceGatedAutonomyController.decide()` (`:290`) and wired into
   `services/intelligence/src/index.js:350`. There is **no TypeSafe reference anywhere in
   the canonical war-room tree** — the seam is unfilled, which is precisely the hazard:
   an ad hoc consumer could map a model opinion to a stronger tier.

3. **The OER fail-close** (`fix/oer-p0-authority-boundary`, commit `c076ccf` "fail close
   local authority boundaries") is the enforcement that makes tier_1 safe to consume. It
   inverts the cost-asymmetry threshold (`alpha = costFN/(costFP+costFN)` → 0.05),
   demotes `AUTONOMOUS_EXECUTION` → `RECOMMEND_AUTOMATION`, and stamps every decision
   with `advisoryOnly:true` / `authority:'NONE'`. Its boundary test
   (`tests/oer-p0-boundary.test.js`, OER-004/005) asserts a self-assertion can never
   become executable authority.

The risk this ADR closes: a TypeSafe judgment — a probabilistic model opinion — being
laundered into evidence strong enough to authorize consequential action. That is exactly
what JAR-EXP-0014/0015 are built to prevent on the research side (advisory-only routing,
`authority_bypassed` always `False`); the same invariant must hold on the consumption
side.

## Decision

The bridge `war-room-typesafe-bridge.js` (proposed landing: war-room
`packages/egac/src/typesafeBridge.js`) is the single translation layer, and it is bound
by five invariants:

- **I1 — tier is hard-coded to `tier_1`.** No code path emits `tier_0` or `tier_2..6`. A
  model opinion can never become a deterministic test, a provider receipt, a
  cryptographic attestation, or a human approval.
- **I2 — every output carries `advisoryOnly:true` and `authority:'NONE'`.** The bridge
  records authority; it never creates it.
- **I3 — only a clean `DISPLAY` judgment counts as `passed:true`.** `REVIEW` never
  passes. `ESCALATE` never passes *and* is flagged `requiresHumanOracle:true`, so a model
  saying "this needs a human" can never satisfy the model gate — it forces a `tier_6`
  human oracle instead.
- **I4 — pure function.** No network, no provider call, no clock read beyond what the
  record already carries, no mutation of inputs.
- **I5 — lineage preserved.** `sourceEvidenceIds` are copied (not aliased) onto the
  emitted item so the evidence chain stays traceable and content-addressed.

### Precondition (load-bearing, not stylistic)

**The bridge may only be wired into a war-room that already carries the `c076ccf` OER
fail-close enforcement.** Wiring it into canonical `main` is a *prohibited configuration*,
because the same lone `tier_1` PASS reaches `AUTONOMOUS_EXECUTION` there. This is not a
recommendation; it is the difference between an advisory signal and an executable one,
and it is proven by execution below.

### Why tier_1 and nothing else (alternatives rejected)

- **Map to `tier_0` (self_assertion)?** Rejected. Understates provenance — a provider
  model response is not a local agent's unverified claim, and mislabeling it corrupts the
  evidence chain's epistemic honesty.
- **Map to `tier_2` (deterministic_test) or higher?** Rejected. False. A 0.45-sensitivity
  model judgment is not a deterministic oracle; doing so is the exact laundering this ADR
  forbids.
- **No bridge — let callers consume `SemanticJudgmentRecord` directly?** Rejected.
  Unbounded laundering risk: every caller re-decides the tier, and the Fihim contract's
  "advisory only" promise has no enforcement point on the consumption side.

## Consequences

**Positive.** The advisory strength of a model opinion is preserved end-to-end. Lineage
is traceable. Malformed input fails closed (throws) rather than guessing a tier. The
bridge is inert authority-wise by construction (I2), so even a buggy consumer cannot read
executable authority out of its output.

**Negative / bounding.** A `tier_1` PASS can never alone authorize action — by design. On
the OER branch a single `tier_1` (FCR model product 0.55) exceeds `alpha` 0.05 and
`2*alpha` 0.10, so it halts. Real autonomy still requires `tier_2+` deterministic
evidence and, for escalation, a `tier_6` human oracle. The bridge delivers *traceable
advisory evidence*, not a shortcut to autonomy.

**Known limitation (caller discipline).** `toSemanticJudgment` (`adapter.ts:15`) defaults
`consequence` to `'LOW'`. A caller that omits consequence on a high-stakes judgment gets
`DISPLAY` routing when confidence ≥ 0.75. This is intentional API ergonomics on the
emitter side and is *bounded* on the consumption side by I1+I3 (worst case it adds one
`tier_1` PASS, which cannot execute alone on OER). Surfaced as a finding, not fixed here —
see `FIHIM-COVERAGE-REVIEW.md`.

## Validation (executed, not asserted)

The harness `verify_typesafe_bridge.mjs` `require()`s the *real* EGAC from two working
copies (canonical `main` `0313ad9` and OER `4a545fb`) plus the local bridge, read-only,
zero-network. Observed output (`verification-output.txt`):

```
PASS  I1_tier_is_always_tier_1
PASS  I2_advisory_only_no_authority
PASS  I3_only_display_passes_escalate_needs_human
PASS  I4_I5_pure_deterministic_lineage_copied
PASS  fail_closed_on_malformed
PASS  case5_OER_fail_close_halts
PASS  case6_canonical_main_gap_executes
PASS  escalate_never_satisfies_gate
---
bridge_invariant_checks=8 failures=0
network_calls=0 foreign_repo_writes=0
verdict=PASS
```

`case5` vs `case6` is the precondition made concrete: identical bridge output, opposite
decisions, because of `c076ccf`. The canary `hermes-pin-projection-smoke.mjs` re-asserts
the OER fail-close and the frozen 0015 pin on a schedule (`canary-output.txt`, 2/2 PASS).

## Reproduction

```sh
# Bridge invariants against the real foreign EGAC (read-only, zero-network):
node evidence/typesafe-cross-repo/verify_typesafe_bridge.mjs

# Hermes canary (pin-smoke + projection-smoke, read-only, zero-network):
node evidence/typesafe-cross-repo/hermes-pin-projection-smoke.mjs
```

Both require the local working copies listed in `INDEX.md` at the pinned commits. If a
working copy is absent the harness SKIPs (exit 2) rather than fabricating a result.

## Non-goals

- This ADR does **not** authorize a live TypeSafe/jev provider call. JAR-EXP-0015 remains
  `NO_GO` until the three human gates (semantic review, owner approval, network
  authorization) are independently satisfied.
- It does **not** modify Fihim, war-room, or Hermes. The bridge is a *proposed* patch;
  the foreign trees are do-not-merge and were read only.
- It does **not** regenerate any signed `dist/` submission bundle.