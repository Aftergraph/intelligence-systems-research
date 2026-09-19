/**
 * Hermes canary: pin-smoke + projection-smoke  (READ-ONLY, ZERO-NETWORK)
 *
 * Proposed as a scheduled Hermes job (see HERMES-CANARY-PROPOSAL.md). It only
 * inspects local working copies and the frozen JAR-EXP-0015 record; it never
 * sends a message, mutates a calendar, opens a socket, or authorizes anything.
 * On any failed invariant it exits non-zero so the cron brief flags it.
 *
 * It is intentionally self-contained (no import of the bridge harness) so it
 * can be dropped into Hermes' nora/model-routing script directory unchanged.
 */

import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);

const JAR15_REPO = 'C:/Users/empir/AppData/Local/Temp/jar15-prereg-verify';
const EXPECTED_PIN = 'dc5d7a94f333908abf09aebe1ca1dbf08f965e604eb2919d0b7a9ca70e149762';
const OER_P0_EGAC = 'C:/Users/empir/workspace/war-room-oer-p0/packages/egac/src/index.js';

const checks = [];
function check(name, fn) {
  try {
    fn();
    checks.push(['PASS', name]);
  } catch (e) {
    checks.push(['FAIL', name, e.message]);
  }
}

// pin-smoke: the frozen 0015 calibration manifest still reproduces the gate pin,
// and the human gates are still closed (NO_GO). Proves the freeze holds and that
// no approval/semantic-review was silently fabricated since landing.
check('pin_smoke_0015_manifest_and_nogo', () => {
  const r = spawnSync('python', ['scripts/verify_jar_exp_0015_semantic_review.py'], {
    cwd: JAR15_REPO,
    encoding: 'utf8',
    timeout: 120000,
  });
  const out = `${r.stdout || ''}\n${r.stderr || ''}`;
  assert.equal(r.status, 0, `verifier exited ${r.status}`);
  assert.ok(out.includes(`calibration_manifest_sha256=${EXPECTED_PIN}`), 'pin drifted from the frozen gate');
  assert.match(out, /preflight_decision=NO_GO/, 'human gates must remain closed (NO_GO)');
  assert.match(out, /verdict=PASS_WITH_FINDINGS/, 'verifier must be green-with-findings');
});

// projection-smoke: the OER fail-close enforcement still holds — a self
// assertion or a lone model judgment can never become executable authority.
// Mirrors war-room tests/oer-p0-boundary.test.js OER-004/005 but self-contained
// and read-only (does not run the foreign suite, only re-asserts the invariant).
check('projection_smoke_oer_fail_close', () => {
  const { EvidenceGatedAutonomyController } = require(OER_P0_EGAC);
  const egac = new EvidenceGatedAutonomyController();
  const selfAssert = egac.decide('Aftergraph/trust-gateway', [{ tier: 'tier_0', passed: true }], ['tier_0']);
  assert.notEqual(selfAssert.decision, 'AUTONOMOUS_EXECUTION', 'self-assertion must never auto-execute');
  assert.equal(selfAssert.advisoryOnly, true);
  assert.equal(selfAssert.authority, 'NONE');
  const tier1 = egac.decide('Aftergraph/trust-gateway', [{ tier: 'tier_1', passed: true }], ['tier_1']);
  assert.notEqual(tier1.decision, 'AUTONOMOUS_EXECUTION');
  assert.equal(tier1.authority, 'NONE');
});

let failed = 0;
for (const c of checks) {
  if (c[0] === 'PASS') console.log(`PASS  ${c[1]}`);
  else { failed += 1; console.log(`FAIL  ${c[1]}  -- ${c[2]}`); }
}
console.log('---');
console.log(`canary_checks=${checks.length} failures=${failed}`);
console.log('external_actions_performed=0 network_calls=0 calendar_mutations=0');
console.log(`verdict=${failed === 0 ? 'PASS' : 'FAIL'}`);
process.exit(failed === 0 ? 0 : 1);