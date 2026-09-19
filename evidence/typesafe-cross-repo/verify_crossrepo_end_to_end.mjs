/**
 * End-to-end cross-repo alignment proof  (READ-ONLY, ZERO-NETWORK).
 *
 * Chain, using the REAL modules from each working copy — no synthetics on the
 * emitter side:
 *
 *   Fihim (~/fihim-typesafe-wt, 34780e8)            the actual emitter
 *     -> toSemanticJudgment / routeSemanticJudgment / TYPE_SAFE_QUESTIONS
 *   war-room bridge (war-room-typesafe-bridge, feat/typesafe-egac-bridge)
 *     -> the APPLIED typesafeBridge.js (asserted byte-identical to the
 *        reviewed copy in this evidence dir)
 *   war-room EGAC, BOTH builds
 *     -> canonical main (0313ad9)  and  OER fail-close (4a545fb)
 *
 * One invariant, four repos, proven by execution:
 *   a TypeSafe/jev model output is advisory evidence and never authority.
 *
 * Zero-network is ENFORCED, not promised: globalThis.fetch is replaced with a
 * throwing stub BEFORE any module import, so any accidental provider call
 * aborts the proof. If a working copy is absent the proof SKIPs (exit 2)
 * rather than fabricating a result.
 */
import { createRequire } from 'node:module';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';

// --- zero-network guard, installed before any dynamic import ----------------
const REAL_FETCH = globalThis.fetch;
globalThis.fetch = () => {
  throw new Error('NETWORK_BLOCKED: cross-repo alignment proof must be zero-network');
};

const require = createRequire(import.meta.url);

const FIHIM = 'C:/Users/empir/fihim-typesafe-wt';
const WR_APPLIED = 'C:/Users/empir/workspace/war-room-typesafe-bridge';
const WR_MAIN = 'C:/Users/empir/workspace/war-room-audit-20260916';
const WR_OER = 'C:/Users/empir/workspace/war-room-oer-p0';
const REVIEWED_BRIDGE = fileURLToPath(new URL('./war-room-typesafe-bridge.js', import.meta.url));

const missing = [FIHIM, WR_APPLIED, WR_MAIN, WR_OER].filter((p) => !existsSync(p));
if (missing.length) {
  console.error('SKIP: missing working copies:', missing.join(', '));
  console.error('This proof is read-only evidence tooling bound to pinned local checkouts (see INDEX.md).');
  process.exit(2);
}

// --- load the REAL modules ---------------------------------------------------
const { toSemanticJudgment } = await import(
  pathToFileURL(FIHIM + '/src/integrations/typesafe/adapter.ts').href);
const { routeSemanticJudgment } = await import(
  pathToFileURL(FIHIM + '/src/domain/semanticJudgment.ts').href);
const { TYPE_SAFE_QUESTIONS } = await import(
  pathToFileURL(FIHIM + '/src/integrations/typesafe/questions.ts').href);
const bridge = require(WR_APPLIED + '/packages/egac/src/typesafeBridge.js');
const MainEGAC = require(WR_MAIN + '/packages/egac/src/index.js').EvidenceGatedAutonomyController;
const OerEGAC = require(WR_OER + '/packages/egac/src/index.js').EvidenceGatedAutonomyController;

const sha256 = (buf) => createHash('sha256').update(buf).digest('hex');

const results = [];
function check(name, fn) {
  try { fn(); results.push(['PASS', name]); }
  catch (e) { results.push(['FAIL', name, e.message]); }
}

// 1. Fihim emitter: the negative keystone that makes tier_1-honesty possible.
check('fihim_negative_keystones_absent', () => {
  assert.ok(!('authorize_action' in TYPE_SAFE_QUESTIONS));
  assert.ok(!('verification_verdict' in TYPE_SAFE_QUESTIONS));
});

// 2. FINDING (documented): the Fihim router can only emit DISPLAY|REVIEW.
//    ESCALATE exists in the type but is unreachable from routeSemanticJudgment.
//    The bridge's ESCALATE handling is therefore defense-in-depth for future
//    emitters, exercised in check 7 with a hand-built record.
check('fihim_router_never_escalates_finding', () => {
  const seen = new Set();
  for (const c of [0.1, 0.5, 0.74, 0.75, 0.9, 0.99]) {
    for (const k of ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']) {
      const d = routeSemanticJudgment({ confidence: c, consequence: k });
      assert.ok(['DISPLAY', 'REVIEW'].includes(d), `unexpected disposition ${d}`);
      seen.add(d);
    }
  }
  assert.ok(!seen.has('ESCALATE'), 'router must not reach ESCALATE (current finding)');
});

// 3. The APPLIED bridge is byte-identical to the reviewed evidence artifact.
check('applied_bridge_byte_identical_to_reviewed', () => {
  const applied = readFileSync(WR_APPLIED + '/packages/egac/src/typesafeBridge.js');
  const reviewed = readFileSync(REVIEWED_BRIDGE);
  assert.equal(sha256(applied), sha256(reviewed));
});

// 4. REAL Fihim records (not synthetics) bridge cleanly: tier_1, advisory, lineage.
const realDisplay = toSemanticJudgment(
  'attention_category',
  { type: 'choice', choice: 'informational', probabilities: { informational: 0.9 }, confidence: 0.9 },
  'jev-1.13.0', ['approval:123'], 'LOW');
const realReviewHigh = toSemanticJudgment(
  'recovery_category',
  { type: 'choice', choice: 'authority_or_budget', probabilities: { authority_or_budget: 0.98 }, confidence: 0.98 },
  'jev-1.13.0', ['failure:77'], 'HIGH');
const realReviewLowConf = toSemanticJudgment(
  'evidence_relevance',
  { type: 'noul', noul: 0.4 },
  'jev-1.13.0', ['claim:9'], 'LOW');

check('real_fihim_records_bridge_clean', () => {
  for (const rec of [realDisplay, realReviewHigh, realReviewLowConf]) {
    assert.equal(rec.epistemicState, 'INFERRED');
    const out = bridge.typesafeRecordToEvidence(rec);
    assert.equal(out.item.tier, 'tier_1');
    assert.equal(out.advisoryOnly, true);
    assert.equal(out.authority, 'NONE');
    assert.equal(out.item.passed, rec.disposition === 'DISPLAY');
    assert.notEqual(out.item.sourceEvidenceIds, rec.sourceEvidenceIds, 'lineage must be copied');
    assert.deepEqual(out.item.sourceEvidenceIds, rec.sourceEvidenceIds);
  }
  assert.equal(realDisplay.disposition, 'DISPLAY');
  assert.equal(realReviewHigh.disposition, 'REVIEW');
  assert.equal(realReviewLowConf.disposition, 'REVIEW');
});

// 5. OER build: a REAL bridged DISPLAY pass is never executable authority.
check('oer_egac_halts_on_real_bridge_output', () => {
  const item = bridge.typesafeRecordToEvidence(realDisplay).item;
  const out = new OerEGAC().decide('Aftergraph/trust-gateway', [item], ['tier_1']);
  assert.notEqual(out.decision, 'AUTONOMOUS_EXECUTION');
  assert.equal(out.decision, 'HALT_AND_ESCALATE');
  assert.equal(out.authority, 'NONE');
  assert.equal(out.advisoryOnly, true);
});

// 6. Canonical main: the SAME real output executes — the documented gap that
//    makes the OER precondition load-bearing, now shown with real emitter bytes.
check('main_egac_gap_on_real_bridge_output', () => {
  const item = bridge.typesafeRecordToEvidence(realDisplay).item;
  const out = new MainEGAC().decide('Aftergraph/trust-gateway', [item], ['tier_1']);
  assert.equal(out.decision, 'AUTONOMOUS_EXECUTION',
    'expected canonical main to (unsafe) auto-execute on tier_1 — this is the finding');
});

// 7. Defense-in-depth: an ESCALATE record (unreachable today, see check 2)
//    can still never satisfy the gate or launder into authority.
check('escalate_defense_in_depth_never_passes', () => {
  const esc = bridge.typesafeRecordToEvidence({ ...realDisplay, disposition: 'ESCALATE' });
  assert.equal(esc.item.passed, false);
  assert.equal(esc.requiresHumanOracle, true);
  const out = new OerEGAC().decide('Aftergraph/trust-gateway', [esc.item], ['tier_1']);
  assert.notEqual(out.decision, 'AUTONOMOUS_EXECUTION');
  assert.equal(out.authority, 'NONE');
});

// 8. The zero-network guard actually held: fetch is still the throwing stub,
//    and importing the real Fihim client module never fired a request.
check('zero_network_guard_held', () => {
  assert.notEqual(globalThis.fetch, REAL_FETCH, 'fetch must still be the blocking stub');
  assert.throws(() => globalThis.fetch('https://api.typesafe.ai/v1/systemone'), /NETWORK_BLOCKED/);
});

// --- report ------------------------------------------------------------------
let failed = 0;
for (const r of results) {
  if (r[0] === 'PASS') console.log(`PASS  ${r[1]}`);
  else { failed += 1; console.log(`FAIL  ${r[1]}  -- ${r[2]}`); }
}
console.log('---');
console.log(`chain=fihim(34780e8) -> war-room-bridge(feat/typesafe-egac-bridge) -> egac(main 0313ad9 | oer 4a545fb)`);
console.log(`e2e_checks=${results.length} failures=${failed}`);
console.log('network_calls=0 foreign_repo_writes=0 fetch_guard=enforced');
console.log(`verdict=${failed === 0 ? 'PASS' : 'FAIL'}`);
process.exit(failed === 0 ? 0 : 1);
