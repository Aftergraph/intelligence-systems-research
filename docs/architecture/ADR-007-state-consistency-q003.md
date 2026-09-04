# ADR-007: Multi-Agent Shared-State Consistency Model

**Document ID:** ADR-007
**Status:** PROPOSED (for owner review)
**Date:** 2026-09-04
**Author:** CONTINUOUS OVERNIGHT MODE (auto-generated)
**Closes:** Q-003 (open_questions.csv, Medium priority)
**Related:** SPEC-001, state/store.py, state/journal.py, state/checkpoint.py

---

## 1. Context

Q-003 (open_questions.csv): *What consistency model is required for
multi-agent shared state (Strict Serializability vs Eventual Consistency)?*

The current implementation (`state/store.py`) is single-process: one
mission, one `DurableStateStore`, no concurrent multi-agent access.
This is fine for Phase 1 of STUDY-011 (the 58 LIVE_VALID runs per
cell), but blocks the Phase 2 multi-agent scenarios (sub-delegation
to multiple workers, parallel exploration of failure-injection
modes). The Q-003 question must be answered before Phase 2 begins.

## 2. Decision Drivers

- **SPEC-001's verification invariant**: the assurance boundary
  (LAB) requires that mission state transitions are linearizable.
  Specifically, `VERIFYING` must be a *single* state that exactly
  one principal can transition out of.
- **Recovery semantics**: `RECOVERING` is by design a state in
  which the mission is paused; concurrent writes are not
  permitted. The recovery logic in `assurance/engine.py` decrements
  `recovery_allowance` and then transitions to `FAILED` or
  `RECOVERING` — this is a read-modify-write that must be atomic.
- **Audit trail**: the EventJournal must record a *complete
  ordering* of events; concurrent writers with eventual
  consistency would create a partial-ordering audit that is
  acceptable for some domains but not for compliance/regulatory
  trails.
- **CAP-theorem trade-off**: in a distributed setting, the
  choice between CP and AP is governed by the tolerance for
  partitioned writes. For mission-critical state, the audit's
  `STUDY-011-READINESS-REPORT.md` documents that the program
  explicitly rejects silent state divergence (a P0 violation).

## 3. Options Considered

### Option A: Strict Serializability (CP in CAP)
- **Pros**: linearizable ordering; matches SPEC-001 verification
  semantics; audit trail is a total order; no surprises in
  recovery (`RECOVERING` state is single-writer).
- **Cons**: high latency under network partition (the
  ConsensusPause); single-region availability during partition.
- **Implementation cost**: requires a consensus protocol
  (Raft, Paxos) or a strongly-consistent KV store (etcd, ZooKeeper).
  Estimated 4-6 weeks of engineering for a working prototype.
- **Match to program**: high. The audit's commitment to
  no-silent-divergence is the strongest argument for SS.

### Option B: Eventual Consistency (AP in CAP)
- **Pros**: low latency, high availability; can use any KV store
  (DynamoDB, Cassandra, FoundationDB).
- **Cons**: concurrent writers can produce conflicting
  transitions (e.g. two workers both setting
  `recovery_allowance = 0` — last-write-wins, which could lose
  recovery context); audit trail is a partial order, harder to
  reason about in compliance reviews.
- **Implementation cost**: low. Standard distributed KV with
  vector clocks.
- **Match to program**: low. The "recover from uncertain external
  effects" semantics in `state/checkpoint.py` would be
  significantly harder to guarantee under EC.

### Option C: Single-Process Serializability (current)
- **Pros**: zero engineering cost; matches the current
  implementation exactly; no partition to handle.
- **Cons**: does not support multi-agent; blocks Phase 2 of
  STUDY-011.
- **Implementation cost**: zero (already done).
- **Match to program**: sufficient for Phase 1 only.

### Option D: Hybrid (Mission-state SS + World-state EC)
- **Pros**: applies SS only where it matters (mission lifecycle,
  criteria status, recovery allowance); uses EC for the
  *workspace* state (file changes, environment variables) where
  eventual consistency is acceptable.
- **Cons**: increased complexity; two systems to maintain; the
  split must be principled.
- **Implementation cost**: medium (2-3 weeks).
- **Match to program**: high. SPEC-001 already separates
  `MissionStateData` (control plane) from `WorldStateData` and
  `AgentStateData`. Promoting this to a "Mission=SS,
  World=EC" split is a natural extension.

## 4. Decision

**Recommend Option D: Hybrid (Mission-state SS + World-state EC)**
for Phase 2, with **Option C retained as a degraded fallback**
when consensus is unavailable.

**Rationale**:

1. SPEC-001's data model already separates the control plane
   (mission lifecycle, criteria status, recovery allowance) from
   the data plane (workspace, environment, agent state). This
   separation is the principled basis for the SS/EC split.
2. The audit's commitment to no-silent-divergence applies
   *only* to the control plane. Workspace state (file changes,
   environment variables) is allowed to be eventually consistent
   because it's reproducible from the audit log + the journal.
3. Option D is incrementally implementable: Phase 1 stays
   single-process (Option C). Phase 2 adds a consensus layer
   (Raft or etcd) only around the control-plane state. The
   data-plane state can stay in the current `DurableStateStore`
   with EC semantics (last-write-wins for non-overlapping keys;
   CRDTs for the small set of fields that need merge semantics).
4. **Failure mode**: if the consensus layer is unavailable,
   the system MUST fail-closed — refuse to transition the
   mission lifecycle. The Q-003 ceiling is the same as Q-005:
   better to halt than to produce a misleading audit trail.

## 5. Consequences

### Positive
- Phase 2 multi-agent scenarios become implementable.
- The control plane retains the no-silent-divergence invariant.
- The data plane can scale horizontally without consensus.
- Audit trail remains a total order over control-plane events.

### Negative
- Two systems to maintain. The split must be documented in
  SPEC-001 §3.2 (state model) and §3.3 (delegation).
- The "consensus unavailable" failure mode is new; it must
  be tested (Q-003 follow-up: a chaos test that takes the
  consensus layer offline and verifies the system halts).
- The data plane's EC semantics must be defined precisely
  (which fields merge, which are LWW).

### Mitigations
- The split is documented in ADR (this document) and pinned
  by tests/test_state_consistency_q003.py (forthcoming).
- The chaos test is in the Q-003 follow-up queue.

## 6. Implementation Plan (Phased)

| Phase | Action | Owner | Gate |
|---|---|---|---|
| 7 | Document the SS/EC split in SPEC-001 §3.2 | SPEC owner | Spec freeze |
| 8 | Implement `ConsensusMissionStore` wrapper around `DurableStateStore` | Runtime team | Compile + 100% existing test pass |
| 8 | Add 5 binding tests in `tests/test_state_consistency_q003.py` | Test author | Test pass |
| 9 | Chaos test: take consensus offline, verify system halts | QA | All 5 tests pass |
| 10 | Phase 2 LIVE_ONLY: validate the SS/EC split under load | Live ops | Q-009 + Q-011 owner gates |

## 7. Open Questions (deferred)

- Q-008 (provider independence) interacts: if the consensus
  cluster is co-located with the primary provider, a provider
  outage could also kill consensus. Multi-region consensus is
  the right answer; the engineering cost is high.
- Q-004 (RFC 8693 binding): if the token exchange layer is
  separate from the consensus layer, who attests to the
  binding? The current design assumes token exchange is
  in-process; this assumption must be revisited for
  distributed consensus.

## 8. References

- SPEC-001 §3.2 (state model)
- SPEC-001 §3.3 (delegation)
- `state/store.py` (current implementation)
- `state/journal.py` (EventJournal)
- `state/checkpoint.py` (CheckpointManager)
- `assurance/engine.py` (LAB — recovery allowance semantics)
- `STUDY-011-READINESS-REPORT.md` (no-silent-divergence invariant)
- AUDIT-EVID-001 (claim registry)

## 9. Reviewer Checklist

- [ ] Does the SS/EC split match the audit's no-silent-divergence
      invariant for the control plane?
- [ ] Is the data-plane EC acceptable for compliance review?
- [ ] Is the "consensus unavailable = fail-closed" failure mode
      tested?
- [ ] Is the multi-region consensus plan in the Q-008 follow-up
      sufficient?
- [ ] Are SPEC-001 §3.2 and §3.3 updated to reflect the split?
