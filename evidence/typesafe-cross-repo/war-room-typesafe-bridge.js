/**
 * TypeSafe -> EGAC tier_1 evidence bridge  (PROPOSED war-room patch)
 *
 * Intended landing location once ratified:
 *   war-room: packages/egac/src/typesafeBridge.js
 *   consumed by: services/intelligence/src/index.js (UnifiedIntelligenceEngine)
 *
 * WHY THIS EXISTS
 * ---------------
 * Fihim emits `SemanticJudgmentRecord` objects from the TypeSafe jev model
 * (src/domain/semanticJudgment.ts). By their own contract those records are
 * "advisory inference only. They never authorize, execute, or verify
 * consequential actions." War-room's EGAC has exactly one slot that matches
 * that epistemic strength: tier_1 / model_judgment (sensitivity 0.45,
 * specificity 0.90). There is no other correct place for a model opinion.
 *
 * This bridge is the single, narrow, fail-closed translation layer. Its
 * invariants ARE the architecture rule in ADR-TYPESAFE-ADVISORY-BOUNDARY.md:
 *
 *   I1  Every TypeSafe judgment maps to tier_1 and ONLY tier_1. The bridge
 *       never emits tier_0 or tier_2..tier_6. A model opinion can never be
 *       laundered into a deterministic test, a provider receipt, an
 *       attestation, or a human approval.
 *   I2  The bridge output always carries advisoryOnly:true and authority:'NONE'.
 *       It records authority; it never creates authority.
 *   I3  disposition==='ESCALATE' is NEVER translated to passed:true. It is
 *       flagged escalate:true / requiresHumanOracle:true so the caller must
 *       seek a tier_6 human oracle. A model saying "this needs a human" can
 *       never satisfy the model gate. REVIEW likewise never passes.
 *   I4  Pure function: no network, no provider call, no clock read beyond what
 *       the record already carries, no mutation of inputs.
 *   I5  Lineage preserved: sourceEvidenceIds are copied (not aliased) onto the
 *       emitted item so the evidence chain stays traceable/content-addressed.
 *
 * PRECONDITION (load-bearing, see verification-output.txt case 5 vs case 6):
 * this bridge may only be wired into a war-room that ALREADY carries the OER
 * fail-close enforcement (commit c076ccf, "fix(war-room): fail close local
 * authority boundaries"). On canonical main the same tier_1 evidence reaches
 * AUTONOMOUS_EXECUTION (alpha 0.95); on the OER branch it halts (alpha 0.05,
 * advisoryOnly, authority NONE). Wiring the bridge before that enforcement
 * would convert advisory model output into an executable autonomy signal.
 */

'use strict';

const POLICY_NOTE =
  'TypeSafe/jev output is tier_1 model_judgment (advisory inference only). ' +
  'It never authorizes, executes, or verifies consequential actions. ' +
  'See ADR-TYPESAFE-ADVISORY-BOUNDARY.md and Fihim src/domain/semanticJudgment.ts.';

const SUPPORTED_DISPOSITIONS = new Set(['DISPLAY', 'REVIEW', 'ESCALATE']);

function isRecord(value) {
  return (
    value &&
    typeof value === 'object' &&
    typeof value.id === 'string' &&
    typeof value.kind === 'string' &&
    value.epistemicState === 'INFERRED' &&
    Array.isArray(value.sourceEvidenceIds) &&
    typeof value.model === 'string' &&
    SUPPORTED_DISPOSITIONS.has(value.disposition)
  );
}

/**
 * Translate one Fihim SemanticJudgmentRecord into an EGAC evidence item.
 * Throws (fail-closed) on anything that is not a well-formed advisory record,
 * rather than guessing a tier.
 */
function typesafeRecordToEvidence(record) {
  if (!isRecord(record)) {
    throw new TypeError(
      'typesafeRecordToEvidence: input is not a well-formed SemanticJudgmentRecord ' +
        '(advisory-only, epistemicState=INFERRED, disposition in DISPLAY|REVIEW|ESCALATE). ' +
        'Refusing to emit evidence for an unrecognized shape.',
    );
  }

  // I1: tier is hard-coded. There is no code path that yields another tier.
  const tier = 'tier_1';

  // I3: only a clean DISPLAY judgment counts as a model pass. REVIEW and
  // ESCALATE never satisfy the gate; ESCALATE additionally demands a human.
  const escalate = record.disposition === 'ESCALATE';
  const passed = record.disposition === 'DISPLAY';

  const item = {
    tier,                                                  // I1
    passed,                                                // I3
    source: 'typesafe:jev',
    judgmentId: record.id,
    judgmentKind: record.kind,
    confidence: record.confidence,
    sourceEvidenceIds: record.sourceEvidenceIds.slice(),   // I5 (copy, not alias)
    model: record.model,
    observedAt: record.observedAt,
  };

  // I2 + I3: the wrapper is where the authority boundary is asserted. EGAC
  // consumes `item` (tier/passed); the wrapper fields are the audit trail
  // proving the bridge never granted authority.
  return {
    item,
    advisoryOnly: true,
    authority: 'NONE',
    escalate,
    requiresHumanOracle: escalate,
    policyNote: POLICY_NOTE,
  };
}

/** Batch helper: map records, fail-closed on the first malformed one. */
function typesafeRecordsToEvidence(records) {
  if (!Array.isArray(records)) {
    throw new TypeError('typesafeRecordsToEvidence: expected an array of records.');
  }
  return records.map(typesafeRecordToEvidence);
}

module.exports = {
  POLICY_NOTE,
  isRecord,
  typesafeRecordToEvidence,
  typesafeRecordsToEvidence,
};