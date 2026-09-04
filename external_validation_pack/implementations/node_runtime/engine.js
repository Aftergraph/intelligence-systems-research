/**
 * Jonas Abde Intelligence Systems Research Program — Q3 2026
 * Clean-Room Node.js / ECMAScript Implementation of SPEC-001 v0.1
 * 
 * ponytail: Zero-dependency Node.js implementation of the 8-tuple <M, S, C, A, B, T, E, V>
 * and Invariants 1-5. Proves language-agnostic implementability from specification alone.
 */

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const VALID_STATES = [
  'DRAFT', 'READY', 'AUTHORIZED', 'RUNNING', 'PAUSED',
  'NEEDS_INPUT', 'VERIFYING', 'VERIFIED', 'RECOVERING',
  'FAILED', 'CANCELLED', 'REVOKED'
];

const TIER_HIERARCHY = {
  'tier_0_self': 0,
  'tier_1_model': 1,
  'tier_2_deterministic': 2,
  'tier_3_attestation': 3
};

class NodeMissionEngine {
  constructor(options = {}) {
    this.state = 'DRAFT';
    this.manifest = null;
    this.mission = null;
    this.delegation = null;
    this.trajectory = [];
    this.evidenceStore = new Map();
    this.budgetTracker = { tokens: 0, cost_usd: 0.0, time_sec: 0.0, actions: 0 };
    this.startTime = null;
    this.prevHash = '0'.repeat(64);
  }

  _appendEvent(eventType, payload = {}) {
    const timestamp = new Date().toISOString();
    const event = {
      id: `evt-${crypto.randomBytes(4).toString('hex')}`,
      timestamp,
      event_type: eventType,
      state: this.state,
      payload
    };

    const canonicalJson = JSON.stringify(event, Object.keys(event).sort());
    const eventHash = crypto.createHash('sha256')
      .update(this.prevHash + canonicalJson)
      .digest('hex');

    event.prev_hash = this.prevHash;
    event.event_hash = eventHash;
    this.prevHash = eventHash;

    this.trajectory.push(event);
    return event;
  }

  loadManifest(manifestPathOrObj) {
    let data = manifestPathOrObj;
    if (typeof manifestPathOrObj === 'string') {
      data = JSON.parse(fs.readFileSync(manifestPathOrObj, 'utf-8'));
    }
    this.manifest = data;
    this._appendEvent('MANIFEST_LOADED', { id: data.metadata?.id || 'unknown' });
    return this.manifest;
  }

  loadMission(missionPathOrObj) {
    let data = missionPathOrObj;
    if (typeof missionPathOrObj === 'string') {
      data = JSON.parse(fs.readFileSync(missionPathOrObj, 'utf-8'));
    }
    if (!data.metadata?.id || !data.objective?.outcome) {
      throw new Error('Invalid Mission: missing metadata.id or objective.outcome');
    }
    this.mission = data;
    this.state = 'READY';
    this._appendEvent('MISSION_INITIALIZED', { mission_id: data.metadata.id });
    return this.mission;
  }

  authorize(delegationObj) {
    if (this.state !== 'READY' && this.state !== 'DRAFT') {
      throw new Error(`Cannot authorize from state ${this.state}`);
    }
    if (!delegationObj.id || !delegationObj.purpose) {
      throw new Error('Invalid delegation: missing id or purpose');
    }

    // Purpose-bound check (Invariant 3)
    if (this.mission && !delegationObj.purpose.includes(this.mission.metadata.id)) {
      throw new Error(`Delegation purpose does not match mission ${this.mission.metadata.id}`);
    }

    this.delegation = delegationObj;
    this.state = 'AUTHORIZED';
    this._appendEvent('DELEGATION_GRANTED', { delegation_id: delegationObj.id });
    return true;
  }

  start() {
    if (this.state !== 'AUTHORIZED') {
      throw new Error(`Cannot start execution from state ${this.state}`);
    }
    this.state = 'RUNNING';
    this.startTime = Date.now();
    this._appendEvent('EXECUTION_COMMENCED', {});
  }

  executeAction(capabilityUri, payload = {}, tokens = 50, costUsd = 0.001) {
    if (this.state === 'REVOKED') throw new Error('PermissionError: Authority revoked');
    if (this.state === 'PAUSED') throw new Error('Runtime is paused');
    if (this.state !== 'RUNNING') throw new Error(`Cannot execute action in state ${this.state}`);

    // 1. Authority Check & Temporal Validation (Invariant 3)
    if (this.delegation) {
      if (this.delegation.revoked) {
        this.state = 'REVOKED';
        throw new Error('PermissionError: Delegation has been revoked');
      }

      const now = new Date();
      if (this.delegation.valid_from && new Date(this.delegation.valid_from) > now) {
        this._appendEvent('CAPABILITY_BLOCKED', { uri: capabilityUri, reason: 'not_yet_valid' });
        throw new Error(`PermissionError: Token not yet valid until ${this.delegation.valid_from}`);
      }
      if (this.delegation.expires_at && new Date(this.delegation.expires_at) < now) {
        this._appendEvent('CAPABILITY_BLOCKED', { uri: capabilityUri, reason: 'expired' });
        throw new Error(`PermissionError: Token expired at ${this.delegation.expires_at}`);
      }

      const allowed = this.delegation.scope?.allowed_capabilities || [];
      const denied = this.delegation.scope?.denied_capabilities || [];

      for (const d of denied) {
        if (d === capabilityUri || (d.endsWith('*') && capabilityUri.startsWith(d.slice(0, -1)))) {
          this._appendEvent('CAPABILITY_BLOCKED', { uri: capabilityUri, reason: 'denied' });
          throw new Error(`PermissionError: Capability ${capabilityUri} denied by rule ${d}`);
        }
      }

      let matched = false;
      for (const a of allowed) {
        if (a === '*' || a === capabilityUri || (a.endsWith('*') && capabilityUri.startsWith(a.slice(0, -1)))) {
          matched = true;
          break;
        }
      }
      if (!matched) {
        this._appendEvent('CAPABILITY_BLOCKED', { uri: capabilityUri, reason: 'unauthorized' });
        throw new Error(`PermissionError: Capability ${capabilityUri} not authorized in scope`);
      }
    }

    // 2. Budget Enforcement (Invariant 4)
    const budget = this.mission?.budget || {};
    const maxTokens = budget.tokens?.max ?? Infinity;
    const maxCost = budget.money?.max ?? Infinity;

    if ((this.budgetTracker.tokens + tokens) > maxTokens) {
      this.state = 'NEEDS_INPUT';
      this._appendEvent('BUDGET_CEILING_HIT', { type: 'tokens' });
      throw new Error('RuntimeError: Token budget ceiling exceeded');
    }

    if ((this.budgetTracker.cost_usd + costUsd) > maxCost) {
      this.state = 'NEEDS_INPUT';
      this._appendEvent('BUDGET_CEILING_HIT', { type: 'money' });
      throw new Error('RuntimeError: Financial budget ceiling exceeded');
    }

    this.budgetTracker.tokens += tokens;
    this.budgetTracker.cost_usd += costUsd;
    this.budgetTracker.actions += 1;
    this._appendEvent('CAPABILITY_INVOKED', { uri: capabilityUri, tokens });

    return { status: 'SUCCESS', uri: capabilityUri };
  }

  finishExecution() {
    // Invariant 1: Non-Equivalence of Completion and Verification
    // Transitions to VERIFYING, strictly never directly to VERIFIED
    if (this.state !== 'RUNNING') {
      throw new Error(`Cannot finish execution from state ${this.state}`);
    }
    this.state = 'VERIFYING';
    this._appendEvent('AGENT_DECLARED_COMPLETE', {});
  }

  recordEvidence(evidenceItem) {
    if (!evidenceItem.criterion_ref || !evidenceItem.tier || !evidenceItem.result) {
      throw new Error('Invalid EvidenceItem: missing required properties');
    }
    // Tier 0 rejection (Invariant 2)
    if (evidenceItem.tier === 'tier_0_self') {
      this._appendEvent('EVIDENCE_REJECTED', { criterion: evidenceItem.criterion_ref, reason: 'tier_0_unsupported' });
      throw new Error('Tier 0 self-assertions are rejected as insufficient evidence');
    }
    this.evidenceStore.set(evidenceItem.criterion_ref, evidenceItem);
    this._appendEvent('EVIDENCE_RECORDED', { criterion: evidenceItem.criterion_ref, tier: evidenceItem.tier });
  }

  evaluateVerification() {
    if (this.state !== 'VERIFYING' && this.state !== 'RECOVERING') {
      throw new Error(`Cannot evaluate verification in state ${this.state}`);
    }

    const required = this.mission?.success?.all || [];
    const minTierName = this.mission?.assurance?.verification?.minimum_tier || 'tier_2_deterministic';
    const minTierVal = TIER_HIERARCHY[minTierName] ?? 2;

    for (const crit of required) {
      const ev = this.evidenceStore.get(crit);
      if (!ev) {
        this.state = 'RECOVERING';
        this._appendEvent('VERIFICATION_FAILED', { missing_criterion: crit });
        return false;
      }
      if (ev.result !== 'SATISFIED') {
        this.state = 'RECOVERING';
        this._appendEvent('VERIFICATION_FAILED', { unsatisfied_criterion: crit });
        return false;
      }
      const itemTierVal = TIER_HIERARCHY[ev.tier] ?? 0;
      if (itemTierVal < minTierVal) {
        this.state = 'RECOVERING';
        this._appendEvent('VERIFICATION_FAILED', { sub_tier_criterion: crit, tier: ev.tier });
        return false;
      }
    }

    this.state = 'VERIFIED';
    this._appendEvent('MISSION_VERIFIED', { verified_criteria_count: required.length });
    return true;
  }

  createSubdelegation(subPrincipal, subCapabilities, validityDurationSeconds = 3600) {
    // Invariant 3: Purpose-bound monotonic attenuation
    if (!this.delegation) throw new Error('No active parent delegation');

    const parentAllowed = this.delegation.scope?.allowed_capabilities || [];
    for (const cap of subCapabilities) {
      const ok = parentAllowed.some(p => p === '*' || p === cap || (p.endsWith('*') && cap.startsWith(p.slice(0, -1))));
      if (!ok) {
        throw new Error(`PermissionError: Cannot grant subcapability ${cap} exceeding parent scope`);
      }
    }

    const parentDepth = this.delegation.scope?.max_delegation_depth ?? 1;
    if (parentDepth <= 0) {
      throw new Error('PermissionError: Maximum delegation depth reached');
    }

    const subToken = {
      id: `del-sub-${crypto.randomBytes(4).toString('hex')}`,
      principal: this.delegation.delegate || 'urn:p:node',
      delegate: subPrincipal,
      purpose: this.delegation.purpose,
      scope: {
        allowed_capabilities: subCapabilities,
        max_delegation_depth: parentDepth - 1
      },
      valid_from: new Date().toISOString(),
      expires_at: new Date(Date.now() + validityDurationSeconds * 1000).toISOString()
    };

    this._appendEvent('SUBDELEGATION_CREATED', { sub_id: subToken.id, delegate: subPrincipal });
    return subToken;
  }

  pause() {
    if (this.state !== 'RUNNING') throw new Error(`Cannot pause from ${this.state}`);
    this.state = 'PAUSED';
    this._appendEvent('EXECUTION_PAUSED', {});
  }

  resume() {
    if (this.state !== 'PAUSED' && this.state !== 'NEEDS_INPUT') {
      throw new Error(`Cannot resume from ${this.state}`);
    }
    this.state = 'RUNNING';
    this._appendEvent('EXECUTION_RESUMED', {});
  }

  revoke(reason = 'Operator revoked') {
    this.state = 'REVOKED';
    if (this.delegation) this.delegation.revoked = true;
    this._appendEvent('AUTHORITY_REVOKED', { reason });
  }
}

module.exports = { NodeMissionEngine, VALID_STATES, TIER_HIERARCHY };
