# SDC-B0 Green-Branch Reconciliation & Independent Verifier Protocol

**Status:** FROZEN BASELINE
**Date:** 2026-09-09
**Parent Track:** #54
**Task:** #58
**Evidence Class:** Engineering protocol only. Not STUDY-012 evidence.

## 1. Purpose

Define the release-side counterweight to high-throughput working branches.
Working branches may contain bounded turbulence. The green candidate MUST
be independently verified before promotion. No worker may self-certify.

## 2. Candidate Snapshot Protocol

At a preregistered interval (default: every 30 minutes during B0 runs):

1. **Freeze**: record exact candidate HEAD SHA per active repo
2. **Stop treating as moving truth**: no new merges to candidate during verification
3. **Dispatch independent verifier**: distinct identity from all workers/planners
4. **Reconcile**: detect overlapping/conflicting changes across worker branches
5. **Verify**: run full test/build/security/evidence checks on frozen candidate
6. **Record stale-base invalidations**: any work based on superseded SHAs
7. **Produce verdict**: SHIP or DO NOT SHIP with machine-readable reasons
8. **Re-freeze if reconciliation changed the snapshot**: if reconciliation merged,
   rebased, or discarded any constituent work, record the NEW candidate SHA and
   re-run verification from step 5 against the updated snapshot. The verdict MUST
   reference the final post-reconciliation SHA, not the original freeze SHA.

## 3. Independent Verifier Role

The verifier MUST be:
- A different process/identity than any worker or planner in the run
- Unable to modify task definitions, governance constraints, or mission scope
- Unable to promote its own work (verifier produces verdicts, not code)
- Bound to the frozen candidate SHA (no mid-verification base updates)

The verifier MAY:
- Run any test, build, lint, security, or evidence check
- Inspect telemetry logs for the candidate's constituent workers
- Reject candidates with unresolved conflicts or failed gates
- Produce structured rejection reasons for replanning

## 4. Stale-Base Detection

A worker's base_sha is stale when:
- origin/main has advanced beyond base_sha AND
- The worker's changes conflict with intervening commits OR
- The worker's tests depend on state modified by intervening commits

Stale-base handling:
1. Record stale-base event in telemetry
2. Mark affected task as `stale`
3. Attempt automatic rebase if conflict-free
4. If conflicts exist: discard worker output, regenerate task with new base
5. Never silently accept stale-base work

## 5. Conflict Reconciliation

When multiple workers modify overlapping files:
1. Detect via git merge-tree or equivalent
2. Prefer earlier-verified work (first-to-green wins)
3. Later conflicting work is rejected with reconciliation-debt penalty
4. If semantic resolution is possible: create reconciliation task
5. Reconciliation tasks are assigned to a dedicated worker, not the original authors

## 6. Verification Gates (B0 Baseline)

For each frozen candidate, the verifier runs:
- [ ] Full test suite passes
- [ ] Lint/format checks pass (or only pre-existing warnings remain)
- [ ] No new security findings (CodeQL/similar)
- [ ] All constituent handoffs have matching head_sha in candidate ancestry
- [ ] No stale-base work included without resolution
- [ ] Telemetry log is complete and parseable for the verification window

Post-B0 treatments add: authority delegation checks, budget conservation,
revocation freshness, release authority separation.

## 7. Verdict Format

```json
{
  "verdict": "SHIP | DO_NOT_SHIP",
  "candidate_sha": "string (final post-reconciliation SHA)",
  "original_freeze_sha": "string (initial freeze SHA before reconciliation)",
  "repository_shas": {"repo_name": "sha", "...": "..."},
  "verified_at": "ISO8601",
  "verifier_id": "string",
  "gates_passed": ["string"],
  "gates_failed": [{"gate": "string", "reason": "string"}],
  "stale_bases_detected": ["string"],
  "conflicts_reconciled": ["string"],
  "reconciliation_debt_delta": 0,
  "refreeze_count": 0,
  "constituent_handoffs_verified": 0,
  "constituent_handoffs_total": 0
}
```

**Multi-repo SHA tracking:** When a run spans multiple repositories, `repository_shas`
records the exact verified SHA for each. The top-level `candidate_sha` is the primary
repo's SHA; all others are captured in the map for full provenance.

## 8. Metrics

Track continuously:
- **Verification queue depth**: candidates awaiting verdict
- **p50/p95 verification latency**: time from freeze to verdict
- **Reconciliation time**: time spent resolving conflicts per candidate
- **Rejected changes count**: worker outputs discarded per cycle
- **Conflict rate**: % of candidates with overlapping worker changes
- **Time-to-green**: time from first worker dispatch to SHIP verdict
- **Semantic progress accepted**: +1 units in verified candidate
- **Semantic progress rejected**: -1 units from discarded work

## 9. Non-Authority

A SHIP verdict means: "this candidate passes all B0 gates."
It does NOT mean:
- The work is institutionally released
- Authority was delegated or attenuated
- Budget was conserved
- Revocation freshness was maintained
- STUDY-012 evidence was generated

Those are post-B0 treatments (G1-G5).

## 10. B0 Scope

This protocol covers baseline green-branch reconciliation only.
It does not implement:
- Mission binding or delegated authority
- Budget tracking or conservation
- Revocation/freshness watermarks
- Release authority separation
- Institutional verification

Those belong to G1-G5 treatment layers.
