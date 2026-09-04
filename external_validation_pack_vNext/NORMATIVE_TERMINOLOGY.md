# SPEC-001 Normative Terminology Reference
**Document ID:** `SPEC-001-TERMS-v0.2`  
**Classification:** Normative Architecture Terminology  
**Standard Track:** IEEE P3709 / IEEE P3777 Profile Integration  

---

## 1. Core Architectural Terms

### 1.1 Non-Equivalence of Complete and Verified ($S_{\text{COMPLETED}} \neq S_{\text{VERIFIED}}$)
- **Candidate Completion (`COMPLETED` / `VERIFYING`):** An operational state in which the executing agent claims to have satisfied task requirements. It is a subjective, unverified claim.
- **Verified Outcome (`VERIFIED`):** An operational state reached *exclusively* when an independent `AssurancePrincipal` confirms that all success criteria are satisfied by deterministic evidence receipts of appropriate tier.

### 1.2 Logical Assurance Boundary
A security and architectural boundary separating stochastic model generation from deterministic verification. Unless explicitly isolated in dedicated container namespaces, this boundary is enforced logically via distinct principal types (`AgentPrincipal` vs. `AssurancePrincipal`). An `AgentPrincipal` is barred from evaluating verification criteria or asserting state transitions to `VERIFIED`.

### 1.3 Hash-Chained Trajectory
An append-only chronological sequence of execution and telemetry events where each event $E_i$ contains the cryptographic hash of its predecessor:
$$H_i = \text{SHA-256}(H_{i-1} \parallel \text{Payload}_i)$$
This structure provides immutable causal ordering and tamper detection without requiring full Merkle trees unless distributed multiparty consensus is needed.

### 1.4 Policy-Constrained Scored Routing
A routing paradigm wherein candidate intelligence models are selected through a deterministic pipeline:
1. **Hard Requirements Filter:** Eliminates models lacking necessary tool or context support.
2. **Policy Filter:** Eliminates providers/models disallowed by security or budget policy.
3. **Multi-Dimensional Scoring:** Evaluates eligible candidates across capability, latency, and cost dimensions.
4. **Receipt Generation:** Emits an immutable `RoutingReceipt` recording candidate scores and selection rationale.

### 1.5 Monotonic Sub-Delegation Attenuation
The invariant that any subagent or delegated process receives authority strictly as a subset of its parent authority:
$$\mathcal{C}_{\text{child}} \subseteq \mathcal{C}_{\text{parent}}, \quad \mathcal{B}_{\text{child}} \le \mathcal{B}_{\text{parent}}, \quad T_{\text{valid, child}} \le T_{\text{valid, parent}}$$
Privilege escalation, purpose expansion, and validity extension are strictly barred.
