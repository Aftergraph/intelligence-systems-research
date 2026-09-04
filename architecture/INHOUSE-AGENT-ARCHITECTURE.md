# In-House Agent Architecture: Systems-Level Integration Architecture
**Program:** Jonas Abde Intelligence Systems Research Program — Q3 2026  
**Document ID:** `ARCH-INHOUSE-001`  
**Classification:** Core Architectural Specification  
**Governing Standard:** SPEC-001 (Mission Contract v0.1)  

---

## 1. Architectural Mission & Philosophy

The In-House Agent is a first-class, vendor-neutral intelligence system designed to execute complex, long-horizon multi-step goals while bound by formal mathematical invariants.

Unlike conventional conversational agent runtimes (e.g., AutoGen, CrewAI, LangGraph, or Hermes) which treat the language model prompt loop as the central source of truth and ambient authority, the In-House Agent decouples **stochastic token generation** from **deterministic systems governance**.

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                              HUMAN EXPERIENCE                                 │
│          Chat / Voice / GUI / CLI / IDE / API / Mobile Experience             │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │ Human Intent, Approvals, Takeover
                                       ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                               MISSION CONTROL                                 │
│  Goal · State · Context · Authority · Budget · Capabilities · Lifecycle       │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │ Bounded Delegation & Progressive View
                                       ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                        IN-HOUSE AGENT EXECUTION LOOP                          │
│                                                                               │
│  Prompt/Context Assembly ──► Model Resolution ──► Model Invocation            │
│            ▲                                             │                    │
│            │                                             ▼                    │
│      State Update ◄── Observation ◄── Capability Dispatch & Policy            │
│            │                                                                  │
│            └─────────────────────────► Candidate Completion                   │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │ Candidate Completion Event ONLY
                                       ▼ (Invariant 1: Complete != Verified)
┌───────────────────────────────────────────────────────────────────────────────┐
│                            MISSION ASSURANCE LOOP                             │
│         Test · Evaluation · Verification · Validation · Evidence              │
│                                                                               │
│                [PASS] ──► Transition to VERIFIED                              │
│                [FAIL] ──► Transition to RECOVERING ──► Return to Exec Loop   │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │ Periodic Anchoring & Evidence Ledger
                                       ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                              DURABLE WORK PLANE                               │
│  Mission State · World State · Agent State · Memory · Trajectory Hash-Chain   │
│         Evidence Store · Artifacts · Cost Telemetry · Checkpoints             │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Distinction: Lifecycle Architecture vs. Runtime Execution Architecture

A critical architectural distinction is enforced between **Lifecycle State Transitions** and **Inner Runtime Execution**:

### 2.1 Lifecycle Architecture (Mission Control Plane)
Governed by finite state machine $\Sigma = \{ \text{DRAFT}, \text{READY}, \text{AUTHORIZED}, \text{RUNNING}, \text{VERIFYING}, \text{VERIFIED}, \text{RECOVERING}, \text{NEEDS\_INPUT}, \text{FAILED}, \text{CANCELLED}, \text{REVOKED} \}$.
- The lifecycle operates out-of-band from the LLM.
- State transitions are strictly validated against pre-conditions and cryptographic evidence.

### 2.2 Runtime Execution Architecture (Inner Execution Loop)
The internal ReAct-style loop of the agent:
$$\text{Assembly} \to \text{Inference} \to \text{Action Request} \to \text{Policy Check} \to \text{Execution} \to \text{Observation} \to \text{Candidate Completion}$$
- The inner execution loop is intentionally treated as a standard, well-understood computational pattern. **We do NOT claim the inner loop itself as novel prior art.**
- Novelty and defensive superiority reside entirely in the **outer systems governance** (Evidence Gating, Monotonic Attenuation, Budget Traps, and Signed Checkpointing).

---

## 3. The Core Invariant: Prohibiting Agent Self-Verification

$$\text{AgentAction} \not\to \text{VERIFIED}$$

1. The In-House Agent is fundamentally incapable of mutating the mission state to `VERIFIED`.
2. When the agent model concludes it has accomplished the mission, it can only emit a `CANDIDATE_COMPLETION` signal.
3. Upon receiving `CANDIDATE_COMPLETION`, the runtime traps the transition and shifts state from `RUNNING` to `VERIFYING`.
4. Only the independent **Mission Assurance Loop** is authorized to evaluate Tier 2 deterministic test receipts or Tier 3 cryptographic attestations.
5. If all required criteria are met, the Assurance Loop issues the state transition `VERIFYING` $\to$ `VERIFIED`.
6. If any criterion fails, the Assurance Loop transitions `VERIFYING` $\to$ `RECOVERING` and injects diagnostic failure receipts back into the agent's execution context.

---

## 4. Multi-Runtime Interoperability

The In-House Agent serves as the first-class native execution engine, but the architecture maintains pluggable adapter boundaries:
- `InHouseAgent` (Primary native implementation)
- `HermesAdapter` (Adapter for Hermes Agent workflows)
- `LangGraphAdapter` (Adapter for LangGraph stategraphs)
- `AutoGenAdapter` (Adapter for AutoGen multi-agent conversable groups)

All external runtimes are subordinated to the same outer Mission Control, Authority, and Assurance loops without altering normative contract semantics.
