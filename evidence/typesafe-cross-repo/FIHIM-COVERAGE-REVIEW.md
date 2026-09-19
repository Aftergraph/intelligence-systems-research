# Fihim `test:typesafe-intelligence` coverage review

- **Date:** 2026-09-19
- **Repo:** `~/fihim-typesafe-wt`, branch `feat/typesafe-intelligence-layer`, HEAD
  `34780e8`, clean working tree.
- **Runner:** `node --experimental-strip-types tests/test-typesafe-intelligence.mjs`
  (Node v24.18.0).
- **Conclusion:** the suite passes and its coverage is sound for the emitter side. **No
  Fihim test change is warranted.** The real gap is on the consumption side (nothing in
  war-room consumes these records today), which is what the bridge + ADR address.

## Observed

```
$ npm --prefix ~/fihim-typesafe-wt run test:typesafe-intelligence
> node --experimental-strip-types tests/test-typesafe-intelligence.mjs
TypeSafe intelligence contract tests passed
```

*(Correction of record: an earlier recon note claimed a missing `questionsForProfile`
import. That was a misread — line 48 **is** the import. The suite is clean.)*

## What the suite pins (all load-bearing for the advisory boundary)

- **Routing dispositions** (`routeSemanticJudgment`): low-confidence → `REVIEW`;
  high-confidence + `HIGH` consequence → `REVIEW` (the consequence guard); high-confidence
  + `LOW` consequence → `DISPLAY`. No path yields an authority verdict.
- **Question-set negatives:** `TYPE_SAFE_QUESTIONS` contains `state_communication_honesty`,
  `attention_category`, `evidence_relevance`; it does **not** contain `authorize_action`
  or `verification_verdict`. This is the contract that makes I1 (tier_1-only) honest — the
  model is never even *asked* an authority question.
- **Adapter lineage + epistemic state:** `toSemanticJudgment` sets `epistemicState:
  'INFERRED'`, copies `sourceEvidenceIds`, and routes via consequence — asserted for both
  a `DISPLAY` case and a `HIGH`-consequence `REVIEW` guard case.
- **Profile narrowing:** `questionsForProfile` returns exactly the expected single key per
  profile (`operator-triage`→`attention_category`, etc.).

## Findings (surfaced, not fixed — emitter-side API is intentional)

1. **Default `consequence = 'LOW'` in `adapter.ts:15`.** A caller that omits consequence
   on a high-stakes judgment gets `DISPLAY` routing when confidence ≥ 0.75. The suite only
   exercises explicit consequence. This is deliberate API ergonomics; the blast radius is
   bounded on the consumption side by bridge I1+I3 (worst case it contributes one
   `tier_1` PASS, which cannot execute alone on an OER-enforced war-room). Recommended
   follow-up for the Fihim owner: consider making `consequence` required at authority-
   sensitive call-sites, or add a lint that flags omitted consequence on `HIGH`/`CRITICAL`
   contexts. Out of scope for this package (would mutate a foreign tree).

2. **Coverage gap is structural, not a missing test.** The emitter is well-tested; the
   *consumer* does not exist in war-room. That absence is the risk (an ad hoc consumer
   could mis-tier), and it is exactly what `war-room-typesafe-bridge.js` +
   `ADR-TYPESAFE-ADVISORY-BOUNDARY.md` close. Hence no Fihim change.

## Net

Emitter contract: verified, advisory-only, negative-keystone enforced. Consumption
contract: proposed bridge + ADR, proven by the cross-repo harness. The two together are
the complete TypeSafe advisory boundary; neither repo is modified by this package.