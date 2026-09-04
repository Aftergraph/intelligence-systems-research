# Durable Work Plane Specification
**Document:** `ARCH-DURABLE-WORK-PLANE-001`  
**Governing Standard:** SPEC-001  

---

## 1. Principle: Conversation History is NOT Canonical State

A foundational architectural flaw in many agent architectures (e.g., standard LangChain or conversational bots) is treating the LLM conversation text buffer (`messages = [...]`) as the primary system state.

In the In-House Agent architecture:
- Conversation history is an **ephemeral, lossy projection** formatted specifically for next-token inference.
- Canonical system state resides exclusively in the **Durable Work Plane**, persisted to structured storage (JSON/SQLite) after every meaningful execution step.

---

## 2. Segregation of State Domains

The Durable Work Plane physically separates seven distinct state domains:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             DURABLE WORK PLANE                              │
│                                                                             │
│  ┌───────────────────────┐  ┌───────────────────────┐  ┌─────────────────┐  │
│  │ 1. Mission State      │  │ 2. World State        │  │ 3. Agent State  │  │
│  │   - Contract Spec (M) │  │   - External Env Refs │  │   - Step index  │  │
│  │   - Lifecycle (Sigma) │  │   - Modified files    │  │   - Active tool │  │
│  │   - Criteria Status   │  │   - Git SHAs          │  │   - Iteration   │  │
│  └───────────────────────┘  └───────────────────────┘  └─────────────────┘  │
│  ┌───────────────────────┐  ┌───────────────────────┐  ┌─────────────────┐  │
│  │ 4. Memory & Context   │  │ 5. Trajectory Ledger  │  │ 6. Evidence     │  │
│  │   - Semantic store    │  │   - SHA-256 Merkle    │  │   - Tier 2/3    │  │
│  │   - Compressed window │  │     Hash Chain        │  │     Receipts    │  │
│  │   - Persistent facts  │  │   - Signed Checkpoints│  │   - Verifier log│  │
│  └───────────────────────┘  └───────────────────────┘  └─────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 7. Telemetry, Budgets & Cost Accounting                               │  │
│  │   - Input/Output Tokens per Provider · Actual USD Burn · Latency      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Crash Recovery and State Reconciliation

The Durable Work Plane guarantees crash resiliency:
$$\text{RUNNING} \xrightarrow{\text{Crash}} \text{Restart} \xrightarrow{\text{Load Checkpoint}} \text{Reconcile External State} \xrightarrow{\text{Resume / Recover}}$$

### Step 1: Checkpoint Loading
On process startup or failure recovery, the runtime reads the latest signed checkpoint from `.intelligence/checkpoints/checkpoint_<mission_id>_<seq>.json`.

### Step 2: World State Reconciliation
Before resuming execution, the engine inspects external environment markers (git working tree, container status, active API locks) to detect any drift that occurred while the agent was down.

### Step 3: Trajectory Verification
The engine recalculates the SHA-256 event hash chain from genesis ($h_0 = \mathcal{H}(M)$) to verify that the local log has not been truncated or tampered with offline.

### Step 4: Resume
If integrity holds, the engine transitions back to `RUNNING` or `VERIFYING` without repeating already-verified sub-tasks.
