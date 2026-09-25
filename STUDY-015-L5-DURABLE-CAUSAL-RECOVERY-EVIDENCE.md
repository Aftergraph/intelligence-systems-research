# STUDY-015 — L5 Durable Causal Recovery Evidence

**Study:** STUDY-015  
**Checkpoint:** L5 Durable Causal Recovery  
**Status:** VERIFIED L5 DURABLE CAUSAL RECOVERY  
**Canonical run:** `36168989907`  
**Evidence class:** `L5_DURABLE_CAUSAL_RECOVERY_CANDIDATE`

## Result

The verified L4 composition was extended across a controlled process crash after the governed remote effect and before independent verification / MissionAcceptance.

Canonical chain:

`effect committed → SIGKILL Trust Gateway + WORKS → restart from durable stores → replay exact Runtime dispatch → recover same execution context → revalidate authority without re-executing effect → exact-head Sentinel verification → subject binding → MissionAcceptance → identical MissionAcceptance retry`

The final run completed successfully on Runtime PR `#210`.

## Exact provenance

- Runtime runner head: `82771872498b8a9896a7eb38289ebfa0e376c1b8`
- Workflow run: `36168989907`
- Artifact ID: `10879866573`
- Artifact ZIP SHA-256: `372102ac73fd0af8eb5607f77e87c5433036fc3706ae1c36247799593cecfc9d`
- Receipt SHA-256: `9bb6d0ed6833d09f7b5e9e0d2b70b3eeb7c3aba922fd887eed3c1e91fced7178`
- STEWARD recovery head: `397c3c0a5b4292f74d7959b1ea21831ffcc12080`
- WORKS recovery head: `b5953f2c6625177ea230b95ea8819170a44001c4`
- Trust Gateway recovery head: `55e734f826fcf6721c0f8f698a7776fa2154a38a`
- AIE head: `bdb36512e57e1bb1f2ec05312d725827267eafc1`
- Sentinel head: `4125f66b0c6d476966feb017ec7ddf3e22ec9459`
- Runtime owner head: `7dc0a336e06e7528f471bbd5676ddb50df6e9046`

## Durable identity recovered after SIGKILL

- mission: `mis_study015_l5_durable_recovery`
- work: `wrk_cdc17edc9e6396e00fc78b07a0038f82`
- WorkerLease: `lse_ec1018fb140953d07f9ece0a16b8f289`
- Runtime dispatch: `rdisp/e74fb76a59b19190`
- WORKS execution: `wexec/idem/study015/live-3`
- execution context: `ctx_62ae40ce4ba8cf61672c9045dc61ceb1`
- trace: `trc_3bb8b58bd9505426da513b1ac057529b`
- action: `act_cccccccccccccccccccccccccccccccc`
- execution PDR: `pdr_3b961bbfd2458373468e79b692109ec3`
- effect: `effect/study015/live-3`
- causal ID: `causal/study015/live-3`
- exact subject: `git:Aftergraph/runtime@efc536b1095715124e2a5455161792f030c974a6`
- Sentinel receipt: `3dd8a87ba63549791b1651534a1d6378672102567f5ce4a806f24fc46999aa84`

## Durability invariants proven in the canonical run

All boolean durability checks were strict `true`:

- WORKS restarted after SIGKILL in explicit recovery mode.
- Same Work, WorkerLease and SQLite DB were recovered.
- Exact Runtime dispatch replay returned the same runtime dispatch, WORKS execution, execution context and trace.
- WORKS execution-context GET returned the durable immutable context after restart.
- Trust Gateway restarted with the same mission, authority and durable audit file.
- The hash-chained audit verified after restart.
- Exactly one matching `git_egress_completed` survived restart.
- The remote proof ref remained the exact committed SHA.
- Re-entering authorization after restart revalidated AIE but did not execute a second Git effect.
- MissionAcceptance committed the Verified Outcome.
- Retrying the identical MissionAcceptance returned the same accepted state.

All prior hostile checks also remained fail-closed.

## Falsification history

The first L5 run, `36168414366`, **failed correctly**.

It found zero persisted `git_egress_completed` events after SIGKILL. Investigation showed that the STUDY-015 Trust Gateway process adapter constructed `Gateway` without the existing `auditFile` option. The core Gateway already supported durable, fsync-per-entry JSONL audit and fail-closed reload; the research adapter had left that facility disabled.

Trust Gateway PR `#136` corrected the adapter and added a restart regression requiring the exact action/effect/execution-context audit receipt to survive chain reload. The canonical L5 run then passed without weakening the durability gate.

The failed run is retained as falsification evidence, not counted as a successful checkpoint.

## Claim boundary

L5 demonstrates controlled crash/restart durability for this pinned composition and fault location. It does not prove arbitrary crash safety, general exactly-once external effects, performance improvement, production readiness, external reproduction, uniqueness or industry superiority.

The receipt keeps:

- `performance_claim=false`
- `g15_9_authorized=false`
- `production_deployment=false`

## Next frontier — L6 Indeterminate Effect Reconciliation

L5 crashes after the effect is externally visible **and** the local completed-effect audit receipt has been durably recorded.

The harder frontier is the uncertainty window:

> The external system may have committed the effect, but the local system has not yet durably learned whether it succeeded.

L6 should inject failure between external commit and local completion receipt. Recovery must reconcile the remote exact state before any retry and prove:

1. no blind re-execution;
2. no false assumption that the effect is absent;
3. exact remote state determines the recovered effect status;
4. one logical effect remains bound to one causal identity;
5. stale/different remote state becomes `INDETERMINATE` or fails closed rather than being self-certified;
6. MissionAcceptance occurs only after independent exact-subject verification.

L6 remains systems-conformance research and does not authorize G15-9.
