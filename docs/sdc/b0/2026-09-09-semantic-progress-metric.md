# SDC-B0 Semantic Progress Metric & Benchmark Selection

**Status:** FROZEN BASELINE
**Date:** 2026-09-09
**Parent Track:** #54
**Task:** #57
**Evidence Class:** Engineering metric definition only. Not STUDY-012 evidence.

## 1. Purpose

Define a semantic-progress score that measures independently accepted
capability movement, NOT raw commit count or tool-call volume.
This metric is the primary success indicator for SDC-B0 continuous runs.

## 2. Benchmark Target

**Repository:** Aftergraph/aie
**Starting SHA:** a0d0830dcad48eecb188832eaa343be4f5bb77af (post Task #61 merge)
**Rationale:** Active implementation track with existing test infrastructure,
CI/CodeQL gates, and known task decomposition (revocation freshness ledger #60).
Suitable for 6-12 hour bounded run.

**Frozen Evidence Cut:** 2026-09-09T21:30:00Z

## 3. Semantic Progress Scoring Rubric

### Positive Units (+1 each)
- Verified bug closure (test added + fix merged + CI green)
- Accepted capability implementation (spec-bound task merged with tests)
- Verified test coverage of previously absent behavior
- Validated performance improvement (benchmark delta > threshold)
- Verified security correction (independent review confirmed)
- Approved protocol/spec completion (frozen document merged)

### Penalties (-1 each)
- Reverted work (merge reverted within same run)
- Duplicate work (same capability implemented twice by different workers)
- Conflicting work (workers produce incompatible changes requiring reconciliation)
- Stale-base invalidation (work discarded due to base drift)
- Unresolved regression (test failure persisting > 2 hours)
- Reconciliation debt (unmerged branches accumulating conflicts)
- Worker false-completion claim (handoff says complete but verifier rejects)
- Human repair required (manual intervention to fix agent output)

### Neutral (0)
- Refactoring without behavioral change
- Documentation updates not bound to spec
- Test-only changes without new coverage
- Dependency bumps without security fix

## 4. Reconciliation Debt Metric

```
reconciliation_debt = sum(
  unmerged_branch_age_hours * conflict_count_per_branch
) / active_worker_count
```

Threshold: > 10.0 triggers mandatory reconciliation pause.

## 5. Human Intervention Counter

Track every human action that:
- Manually merges/reverts a branch
- Fixes code outside normal review flow
- Overrides a verifier verdict
- Unblocks a stuck worker manually
- Adjusts task scope mid-run

Human interventions are logged as telemetry events and count as -1 penalty
each (indicates system could not self-resolve).

## 6. Task Generation Policy

Tasks are generated from:
1. Open issues in binding implementation ledger (#60 for AIE)
2. Spec-defined task sequences (Tasks 2-7 in revocation freshness plan)
3. Verification failures requiring remediation
4. Stale-base recovery tasks

Tasks MUST have:
- Binding spec reference
- Acceptance criteria
- Expected evidence list
- Scope constraints
- Parent task dependency chain

## 7. Stop/Abort Criteria

**Hard stop (immediate):**
- Security credential exposure detected
- Worker escapes sandbox/worktree boundary
- Disk space < 5GB free
- RAM pressure causes OOM kills
- > 5 consecutive worker crashes without recovery

**Soft stop (graceful wind-down):**
- Semantic progress score <= -5
- Reconciliation debt > 20.0
- All executable tasks blocked > 1 hour
- Run duration exceeds preregistered limit (12h)
- Human intervention count > 10

## 8. Preregistered Analysis Fields

Before any B0 long run starts, freeze:
- [ ] Starting SHA per repo
- [ ] Task generation seed/policy
- [ ] Semantic progress scoring weights
- [ ] Reconciliation debt thresholds
- [ ] Abort criteria values
- [ ] Expected run duration
- [ ] Resource allocation limits
- [ ] Independent verifier identity

Post-run analysis compares observed vs. preregistered values.
No field may be adjusted after observing results unless the run
is invalidated and restarted as a new preregistered run.

## 9. Evidence Honesty

Semantic progress scores are ENGINEERING METRICS for B0 baseline measurement.
They are NOT:
- Research evidence for STUDY-012
- Proof of self-driving capability
- Release authority
- Institutional verification

Only frozen valid experimental protocols generate research evidence.
