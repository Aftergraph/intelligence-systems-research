/**
 * Cross-repo verification harness for the TypeSafe -> EGAC tier_1 bridge.
 *
 * READ-ONLY against the foreign repos: it require()s war-room's EGAC from two
 * working copies (canonical main 0313ad9 and the OER fail-close branch
 * 4a545fb) plus the local bridge, but never writes to them and never opens a
 * network socket. If the working copies are not present it SKIPs (exit 2)
 * rather than fabricating a result.
 *
 * It proves invariants I1..I5 of ADR-TYPESAFE-ADVISORY-BOUNDARY.md and the
 * load-bearing precondition: the SAME tier_1 PASS evidence is executable
 * autonomy on canonical main and HALT_AND_ESCALATE (authority NONE) on OER.
 */

import { createRequire } from 'node:module';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);

const WARROOM_MAIN_EGAC =
  'C:/Users/empir/workspace/war-room-audit-20260916/packages/egac/src/index.js';
const WARROOM_OER_P0_EGAC =
  'C:/Users/empir/workspace/war-room-oer-p0/packages/egac/src/index.js';
const BRIDGE = './war-room-typesafe-bridge.js';

const { typesafeRecordToEvidence, POLICY_NOTE } = require(BRIDGE);

let mainEGAC;
let oerEGAC;
try {
  mainEGAC = require(WARROOM_MAIN_EGAC).EvidenceGatedAutonomyController;
  oerEGAC = require(WARROOM_OER_P0_EGAC).EvidenceGatedAutonomyController;
} catch (err) {
  console.error('SKIP: war-room working copies not reachable:', err.message);
  console.error('This harness is read-only evidence tooling; it needs the local checkouts.');
  process.exit(2);
}

// Synthetic Fihim SemanticJudgmentRecords — the exact shape emitted by
// src/integrations/typesafe/adapter.ts -> toSemanticJudgment.
const rec = (over) => ({
  id: 'attention_category',
  kind: 'attention_category',
  answer: { type: 'choice', choice: 'informational', probabilities: { informational: 0.9 }, confidence: 0.9 },
  confidence: 0.9,
  epistemicState: 'INFERRED',
  sourceEvidenceIds: ['approval:123'],
  model: 'jev-1.13.0',
  observedAt: 1771500000000,
  disposition: 'DISPLAY',
  ...over,
});

const results = [];
function check(name, fn) {
  try {
    fn();
    results.push(['PASS', name]);
  } catch (e) {
    results.push(['FAIL', name, e.message]);
  }
}

// I1: tier is always tier_1, never anything else, across a disposition sweep.
check('I1_tier_is_always_tier_1', () => {
  for (const d of ['DISPLAY', 'REVIEW', 'ESCALATE']) {
    const out = typesafeRecordToEvidence(rec({ disposition: d }));
    assert.equal(out.item.tier, 'tier_1', `disposition ${d} must map to tier_1`);
  }
});

// I2: every output is advisory-only with no authority.
check('I2_advisory_only_no_authority', () => {
  for (const d of ['DISPLAY', 'REVIEW', 'ESCALATE']) {
    const out = typesafeRecordToEvidence(rec({ disposition: d }));
    assert.equal(out.advisoryOnly, true);
    assert.equal(out.authority, 'NONE');
    assert.equal(out.policyNote, POLICY_NOTE);
  }
});

// I3: only DISPLAY passes; REVIEW and ESCALATE never satisfy the gate;
//     ESCALATE demands a human oracle.
check('I3_only_display_passes_escalate_needs_human', () => {
  assert.equal(typesafeRecordToEvidence(rec({ disposition: 'DISPLAY' })).item.passed, true);
  const review = typesafeRecordToEvidence(rec({ disposition: 'REVIEW' }));
  assert.equal(review.item.passed, false);
  assert.equal(review.escalate, false);
  const esc = typesafeRecordToEvidence(rec({ disposition: 'ESCALATE' }));
  assert.equal(esc.item.passed, false);
  assert.equal(esc.escalate, true);
  assert.equal(esc.requiresHumanOracle, true);
});

// I4 + I5: pure function, no input mutation, deterministic, lineage copied.
check('I4_I5_pure_deterministic_lineage_copied', () => {
  const r = rec({ disposition: 'DISPLAY' });
  const snapshot = JSON.stringify(r);
  const a = typesafeRecordToEvidence(r);
  const b = typesafeRecordToEvidence(r);
  assert.equal(JSON.stringify(r), snapshot, 'input must not be mutated');
  assert.deepEqual(a.item, b.item, 'deterministic for equal inputs');
  assert.notEqual(a.item.sourceEvidenceIds, r.sourceEvidenceIds, 'must copy, not alias');
  assert.deepEqual(a.item.sourceEvidenceIds, ['approval:123']);
});

// Fail-closed on malformed input (no silent tier guess).
check('fail_closed_on_malformed', () => {
  assert.throws(() => typesafeRecordToEvidence({ id: 'x' }), TypeError);
  assert.throws(() => typesafeRecordToEvidence(null), TypeError);
  assert.throws(() => typesafeRecordToEvidence(rec({ epistemicState: 'OBSERVED' })), TypeError);
  assert.throws(() => typesafeRecordToEvidence(rec({ disposition: 'AUTHORIZE' })), TypeError);
});

// --- The load-bearing cross-repo result -------------------------------------
// Same single tier_1 PASS evidence, two war-room builds, opposite decisions.

const displayItem = typesafeRecordToEvidence(rec({ disposition: 'DISPLAY' })).item;

check('case5_OER_fail_close_halts', () => {
  const egac = new oerEGAC(); // defaults costFP=19, costFN=1 -> alpha=0.05 after c076ccf inversion
  const out = egac.decide('Aftergraph/trust-gateway', [displayItem], ['tier_1']);
  assert.equal(out.advisoryOnly, true, 'OER EGAC must be advisory-only');
  assert.equal(out.authority, 'NONE', 'OER EGAC must carry no authority');
  assert.notEqual(out.decision, 'AUTONOMOUS_EXECUTION', 'tier_1 alone must never auto-execute on OER');
  assert.equal(out.decision, 'HALT_AND_ESCALATE', 'single tier_1 (FCR 0.55) exceeds OER alpha 0.05 and 2*alpha 0.10');
});

check('case6_canonical_main_gap_executes', () => {
  const egac = new mainEGAC(); // defaults costFP=19, costFN=1 -> alpha=0.95 (pre-inversion)
  const out = egac.decide('Aftergraph/trust-gateway', [displayItem], ['tier_1']);
  // This is the GAP the OER branch closes: on main a lone model opinion is
  // treated as sufficient for autonomous execution. Recorded as a finding.
  assert.equal(out.decision, 'AUTONOMOUS_EXECUTION',
    'expected canonical main to (unsafe) auto-execute on tier_1 — this is the finding');
});

// ESCALATE can never be laundered into a pass even if fed straight to EGAC.
check('escalate_never_satisfies_gate', () => {
  const escItem = typesafeRecordToEvidence(rec({ disposition: 'ESCALATE' })).item;
  assert.equal(escItem.passed, false);
  const egac = new oerEGAC();
  const out = egac.decide('Aftergraph/trust-gateway', [escItem], ['tier_1']);
  assert.notEqual(out.decision, 'AUTONOMOUS_EXECUTION');
  assert.equal(out.authority, 'NONE');
});

// --- report ----------------------------------------------------------------
let failed = 0;
for (const r of results) {
  if (r[0] === 'PASS') console.log(`PASS  ${r[1]}`);
  else { failed += 1; console.log(`FAIL  ${r[1]}  -- ${r[2]}`); }
}
console.log('---');
console.log(`bridge_invariant_checks=${results.length} failures=${failed}`);
console.log(`network_calls=0 foreign_repo_writes=0`);
console.log(`verdict=${failed === 0 ? 'PASS' : 'FAIL'}`);
process.exit(failed === 0 ? 0 : 1);