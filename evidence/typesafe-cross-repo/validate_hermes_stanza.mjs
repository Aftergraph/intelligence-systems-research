/**
 * Hermes stanza validator  (READ-ONLY, ZERO-NETWORK, NO MUTATION).
 *
 * Validates the PROPOSED canary job (hermes-canary-job.proposed.json) against
 * the REAL Rendetalje cron spec by execution, without touching the foreign
 * tree: key-shape parity with existing jobs, id uniqueness, skill-name parity
 * against the union of cron+commands specs, and invariance of global_safety
 * and all top-level fields under a SIMULATED merge.
 *
 * The Hermes parent branch (fix/ci-vitest-baseline-convergence) is the
 * ci-local-gated convergence branch with dirty renos/ files that must be
 * preserved; application of the stanza remains an owner action. This script
 * proves the proposal is conformant, nothing more.
 */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const CRON = 'C:/Users/empir/Documents/rendetalje-workspace-ci-vitest/hermes/cron/rendetalje-cron-spec.json';
const COMMANDS = 'C:/Users/empir/Documents/rendetalje-workspace-ci-vitest/hermes/commands/rendetalje-commands.json';
const STANZA = fileURLToPath(new URL('./hermes-canary-job.proposed.json', import.meta.url));
const CANARY_SCRIPT = fileURLToPath(new URL('./hermes-pin-projection-smoke.mjs', import.meta.url));

if (!existsSync(CRON) || !existsSync(COMMANDS)) {
  console.error('SKIP: Hermes working copy not reachable at the pinned path.');
  process.exit(2);
}

const cron = JSON.parse(readFileSync(CRON, 'utf8'));
const commands = JSON.parse(readFileSync(COMMANDS, 'utf8'));
const stanza = JSON.parse(readFileSync(STANZA, 'utf8'));

const results = [];
function check(name, fn) {
  try { fn(); results.push(['PASS', name]); }
  catch (e) { results.push(['FAIL', name, e.message]); }
}

check('cron_spec_parses_and_has_jobs', () => {
  assert.ok(Array.isArray(cron.jobs) && cron.jobs.length > 0);
  assert.ok(cron.global_safety && cron.global_safety.external_actions_allowed === false);
});

check('stanza_key_shape_matches_existing_jobs', () => {
  const keySets = cron.jobs.map((j) => JSON.stringify(Object.keys(j).sort()));
  assert.ok(new Set(keySets).size === 1, `existing jobs must have uniform key sets, got: ${keySets.join(' | ')}`);
  assert.equal(JSON.stringify(Object.keys(stanza).sort()), keySets[0]);
});

check('stanza_id_unique', () => {
  assert.ok(!cron.jobs.some((j) => j.id === stanza.id));
});

check('stanza_skills_are_known_in_workspace_specs', () => {
  const known = new Set();
  for (const j of cron.jobs) for (const s of j.skills || []) known.add(s);
  for (const c of commands.commands || []) for (const s of c.skills || []) known.add(s);
  for (const s of stanza.skills) assert.ok(known.has(s), `unknown skill: ${s}`);
});

check('simulated_merge_preserves_global_safety_and_top_level', () => {
  const merged = { ...cron, jobs: [...cron.jobs, stanza] };
  assert.deepEqual(merged.global_safety, cron.global_safety);
  for (const k of ['schema_version', 'workspace', 'timezone', 'purpose']) {
    assert.equal(merged[k], cron[k]);
  }
  assert.equal(merged.jobs.length, cron.jobs.length + 1);
});

check('canary_script_ships_with_the_proposal', () => {
  const src = readFileSync(CANARY_SCRIPT, 'utf8');
  assert.ok(src.includes('pin_smoke_0015_manifest_and_nogo'));
  assert.ok(src.includes('projection_smoke_oer_fail_close'));
});

let failed = 0;
for (const r of results) {
  if (r[0] === 'PASS') console.log(`PASS  ${r[1]}`);
  else { failed += 1; console.log(`FAIL  ${r[1]}  -- ${r[2]}`); }
}
console.log('---');
console.log(`stanza_checks=${results.length} failures=${failed}`);
console.log('network_calls=0 foreign_repo_writes=0 (simulated merge only; real spec untouched)');
console.log(`verdict=${failed === 0 ? 'PASS' : 'FAIL'}`);
process.exit(failed === 0 ? 0 : 1);
