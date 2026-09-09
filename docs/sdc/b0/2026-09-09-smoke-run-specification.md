# SDC-B0 Smoke Run Specification

**Status:** DRAFT
**Date:** 2026-09-09
**Parent Track:** #54
**Evidence Class:** Engineering experiment only (NOT STUDY-012 confirmatory)

## Objective

Validate that the B0 execution architecture can sustain a short continuous run before launching the preregistered 6-12 hour experiment.

## Prerequisites (must be frozen before smoke)

- [x] B0 recursive planner/worker baseline protocol (#55) — PR #60 OPEN, review fixes in progress
- [x] VDS execution telemetry schema (#56) — PR #61 OPEN, review fixes in progress
- [x] Semantic-progress metric (#57) — PR #62 OPEN, review fixes in progress
- [x] Green-branch reconciliation protocol (#58) — PR #63 OPEN, review fixes in progress
- [ ] All four PRs merged to main
- [ ] Telemetry ingestion pipeline operational
- [ ] WorkerSandbox interface implemented for HermesWorktreeSandbox (B0 canonical backend)
- [ ] Starting SHA frozen for benchmark repository
- [ ] Abort conditions defined

## Smoke Run Acceptance Criteria

The smoke run PASSES if ALL of the following are observed:

1. **Root planner dispatch**: Root planner successfully decomposes a test mission into ≥2 subtasks
2. **Subplanner recursion**: At least one subplanner further decomposes its scope
3. **Concurrent isolated workers**: ≥2 workers operate simultaneously in separate worktrees without collision
4. **Handoff propagation**: Every completed worker produces a structured handoff that reaches the parent planner
5. **Telemetry reconstruction**: The full task graph (planner → subplanner → worker) can be reconstructed from telemetry events
6. **Failed worker recovery**: At least one simulated worker failure is handled without killing the run
7. **Stale-base handling**: At least one stale-base detection event is recorded and handled
8. **Independent green verification**: A verification pass runs against a candidate branch, producing SHIP or DO NOT SHIP

## Duration

Target: 30 minutes maximum. This is a validation run, not a measurement run.

## Benchmark Repository

TBD — select a small Aftergraph repo with fast test suite (< 60s) and ≥2 independent modules.

## Starting SHA

TBD — freeze after all B0 protocol PRs merge.

## Abort Conditions

- Worker process crash without recovery within 60s
- Telemetry pipeline fails to ingest events for > 30s
- Worktree collision detected (two workers writing same path)
- Disk usage exceeds 85%
- Memory pressure causes OOM kill
- Planner enters infinite replan loop (> 5 replans without progress in 5 minutes)

## Resource Budget

- Max 3 concurrent workers (conservative; VDS has 6 cores, 14Gi RAM free)
- Max 10GB additional disk for worktrees and artifacts
- Network disabled for workers by default

## Evidence Preservation

All telemetry events, handoffs, planner state snapshots, and git operations must be preserved under `/root/workspace/aftergraph/smoke-runs/<run-id>/`.

## Post-Smoke Actions

If PASS: Freeze B0 evidence, proceed to preregistered 6-12 hour run.
If FAIL: Record failure mode, fix root cause, re-run smoke after fix verification.
