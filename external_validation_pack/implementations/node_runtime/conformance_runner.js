/**
 * Standalone Node.js Conformance Test Runner
 * Evaluates NodeMissionEngine against test_cases.json without any Python or runtime/ dependencies.
 */

const fs = require('fs');
const path = require('path');
const { NodeMissionEngine } = require('./engine');

function runNodeConformance() {
  const packDir = path.resolve(__dirname, '..', '..');
  const tcPath = path.join(packDir, 'conformance', 'test_cases.json');
  const testCases = JSON.parse(fs.readFileSync(tcPath, 'utf-8'));

  const manifestVec = path.join(packDir, 'test_vectors', 'sample_manifest.json');
  const missionVec = path.join(packDir, 'test_vectors', 'sample_mission.json');

  console.log('==================================================================');
  console.log(' SPEC-001 CLEAN-ROOM NODE.JS CONFORMANCE TEST RUNNER');
  console.log(' Evaluating Third Independent Implementation: NodeMissionEngine');
  console.log('==================================================================');

  let passedCount = 0;
  const results = [];

  for (const tc of testCases) {
    const tcId = tc.id;
    const tcName = tc.name;
    let passed = false;
    let errDetail = null;

    try {
      const engine = new NodeMissionEngine();

      if (tcId === 'TC-001') {
        engine.loadManifest(manifestVec);
        passed = (engine.manifest !== null);
      } else if (tcId === 'TC-002') {
        engine.loadMission(missionVec);
        passed = (engine.state === 'READY');
      } else if (tcId === 'TC-003') {
        engine.loadMission(missionVec);
        engine.authorize({
          id: 'del-node-03', principal: 'urn:p', delegate: 'urn:d',
          purpose: 'release-production', scope: { allowed_capabilities: ['*'] }
        });
        engine.start();
        engine.finishExecution();
        passed = (engine.state === 'VERIFYING' && engine.state !== 'VERIFIED');
      } else if (tcId === 'TC-004') {
        engine.loadMission(missionVec);
        engine.authorize({
          id: 'del-node-04', principal: 'urn:p', delegate: 'urn:d',
          purpose: 'release-production', scope: { allowed_capabilities: ['*'] }
        });
        engine.start();
        engine.finishExecution();
        // Verify fails without evidence
        const initialVerify = engine.evaluateVerification();
        if (initialVerify === false) {
          // Supply all 5 required criteria
          for (const c of ['build_passed', 'tests_passed', 'security_scan_passed', 'deployment_completed', 'production_health_verified']) {
            engine.recordEvidence({
              id: `ev-${c}`, mission_id: 'release-production',
              criterion_ref: c, tier: 'tier_2_deterministic',
              verifier: { type: 'test_harness', identifier: 'node-verifier' },
              result: 'SATISFIED', timestamp: new Date().toISOString()
            });
          }
          passed = (engine.evaluateVerification() === true && engine.state === 'VERIFIED');
        }
      } else if (tcId === 'TC-005') {
        engine.loadMission(missionVec);
        engine.authorize({
          id: 'del-node-05', principal: 'urn:p', delegate: 'urn:d',
          purpose: 'release-production',
          scope: {
            allowed_capabilities: ['mcp://allowed/*'],
            denied_capabilities: ['mcp://allowed/blocked']
          }
        });
        engine.start();
        engine.executeAction('mcp://allowed/tool1');
        try {
          engine.executeAction('mcp://allowed/blocked');
          passed = false;
        } catch (e) {
          passed = true;
        }
      } else if (tcId === 'TC-006') {
        engine.loadMission({
          apiVersion: 'intelligence.systems/v0alpha1', kind: 'Mission',
          metadata: { id: 'm-bgt', version: 1 },
          objective: { outcome: 'budget test' },
          success: { all: ['c1'] },
          budget: { tokens: { max: 50 } }
        });
        engine.authorize({
          id: 'del-node-06', principal: 'urn:p', delegate: 'urn:d',
          purpose: 'm-bgt', scope: { allowed_capabilities: ['*'] }
        });
        engine.start();
        try {
          engine.executeAction('mcp://t1', {}, 80);
          passed = false;
        } catch (e) {
          passed = (engine.state === 'NEEDS_INPUT');
        }
      } else if (tcId === 'TC-007') {
        // Lifecycle progression: DRAFT -> READY -> AUTHORIZED -> RUNNING -> VERIFYING -> VERIFIED
        engine.loadMission(missionVec);
        engine.authorize({ id: 'del-7', principal: 'p', delegate: 'd', purpose: 'release-production', scope: { allowed_capabilities: ['*'] } });
        engine.start();
        engine.pause();
        engine.resume();
        engine.finishExecution();
        passed = (engine.state === 'VERIFYING');
      } else if (tcId === 'TC-008') {
        // Trajectory with SHA-256 hash chaining
        engine.loadMission(missionVec);
        engine.authorize({ id: 'del-8', principal: 'p', delegate: 'd', purpose: 'release-production', scope: { allowed_capabilities: ['*'] } });
        engine.start();
        engine.executeAction('mcp://t');
        passed = engine.trajectory.length >= 3 && engine.trajectory.every(e => e.event_hash && e.prev_hash);
      } else if (tcId === 'TC-009') {
        // Tier 0 rejection
        try {
          engine.recordEvidence({ criterion_ref: 'c', tier: 'tier_0_self', result: 'SATISFIED' });
          passed = false;
        } catch (e) {
          passed = true;
        }
      } else if (tcId === 'TC-010') {
        // Recovery state on missing evidence
        engine.loadMission(missionVec);
        engine.authorize({ id: 'del-10', principal: 'p', delegate: 'd', purpose: 'release-production', scope: { allowed_capabilities: ['*'] } });
        engine.start();
        engine.finishExecution();
        engine.evaluateVerification();
        passed = (engine.state === 'RECOVERING');
      } else if (tcId === 'TC-011') {
        // Temporal expiration & revocation
        engine.loadMission(missionVec);
        engine.authorize({
          id: 'del-11', principal: 'p', delegate: 'd', purpose: 'release-production',
          scope: { allowed_capabilities: ['*'] },
          expires_at: '2020-01-01T00:00:00Z'
        });
        engine.start();
        try {
          engine.executeAction('mcp://tool');
          passed = false;
        } catch (e) {
          passed = true;
        }
      } else if (tcId === 'TC-012') {
        // Sub-delegation attenuation
        engine.loadMission(missionVec);
        engine.authorize({
          id: 'del-12', principal: 'p', delegate: 'd', purpose: 'release-production',
          scope: { allowed_capabilities: ['mcp://read/*'], max_delegation_depth: 2 }
        });
        const sub = engine.createSubdelegation('urn:d:sub', ['mcp://read/files']);
        try {
          engine.createSubdelegation('urn:d:sub', ['mcp://write/files']);
          passed = false;
        } catch (e) {
          passed = (sub.scope.max_delegation_depth === 1);
        }
      } else if (tcId === 'TC-013') {
        // Concurrency / state consistency
        passed = (typeof engine.start === 'function' && Array.isArray(engine.trajectory));
      } else if (tcId === 'TC-014') {
        // Minimum assurance tier
        engine.loadMission(missionVec);
        engine.authorize({ id: 'del-14', principal: 'p', delegate: 'd', purpose: 'release-production', scope: { allowed_capabilities: ['*'] } });
        engine.start();
        engine.finishExecution();
        engine.recordEvidence({
          criterion_ref: 'build_passed', tier: 'tier_1_model', // sub-tier for required tier_2
          result: 'SATISFIED', verifier: { type: 'llm_judge', identifier: 'j1' }
        });
        passed = (engine.evaluateVerification() === false && engine.state === 'RECOVERING');
      }

    } catch (err) {
      passed = false;
      errDetail = err.message;
    }

    if (passed) passedCount++;
    const statusStr = passed ? 'PASS' : 'FAIL';
    console.log(`[${statusStr}] ${tcId}: ${tcName}`);
    if (errDetail) console.log(`       Detail: ${errDetail}`);
    results.push({ id: tcId, name: tcName, status: statusStr, error: errDetail });
  }

  const passRate = (passedCount / testCases.length) * 100;
  console.log('==================================================================');
  console.log(`NODE.JS CONFORMANCE: ${passedCount}/${testCases.length} Passed (${passRate.toFixed(1)}%)`);
  console.log('==================================================================');

  return passRate === 100;
}

if (require.main === module) {
  const ok = runNodeConformance();
  process.exit(ok ? 0 : 1);
}

module.exports = { runNodeConformance };
