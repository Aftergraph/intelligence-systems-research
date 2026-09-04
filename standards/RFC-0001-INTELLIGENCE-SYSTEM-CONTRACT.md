# RFC 0001: Intelligence System Contract and Verification Protocol
**Author:** Jonas Abde  
**Working Group:** Open Intelligence Systems Working Group (OIS-WG) / IEEE SA Candidate  
**Category:** Standards Track  
**Date:** September 2026  
**Status:** PROPOSED STANDARD RFC  

---

## Abstract
This document specifies the **Intelligence System Contract and Verification Protocol (ISC-VP)**, a vendor-neutral machine-readable contract and execution protocol for coordinating autonomous artificial intelligence agents, models, and tools. ISC-VP formally decouples agent execution completion from outcome verification, introduces purpose-bound authority attenuation derived from OAuth 2.0 Token Exchange (RFC 8693), and establishes a deterministic evidence-gated lifecycle across heterogeneous runtimes.

---

## 1. Introduction & Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC2119] [RFC8174].

---

## 2. System Model and Invariants

An Intelligent System instance executing under this specification MUST implement the formal 8-tuple model:
$$\text{IS} = \langle M, S, C, A, B, T, E, V \rangle$$

### 2.1 Normative Invariants
A conforming implementation MUST enforce the following five invariants:

1. **Invariant 1 (Non-Equivalence of Completion and Verification):**
   $$\text{Complete}(M) \not\implies \text{Verified}(M)$$
   When an agent signals execution conclusion, the runtime MUST transition the mission to state `VERIFYING`. The runtime MUST NOT permit an agent to transition a mission directly to `VERIFIED`.

2. **Invariant 2 (Evidence-Gated Completion):**
   $$\text{Verified}(M) \iff \forall k \in \mathcal{K}, \exists e \in E : V(k, e) = \text{SATISFIED}$$
   Transition to state `VERIFIED` MUST require independent evaluation of structured `EvidenceItem` records against all acceptance criteria specified in the contract. Self-assertions emitted by the agent (Tier 0) MUST NOT satisfy acceptance criteria.

3. **Invariant 3 (Purpose-Bound Authority Attenuation):**
   $$\forall a \in A_{\text{subagent}}, \quad a \subseteq A_{\text{parent}} \quad \land \quad \text{Purpose}(a) \subseteq \text{Purpose}(A_{\text{parent}})$$
   Any sub-delegation token minted by an agent MUST strictly attenuate permissions, decrement delegation depth, and maintain an expiration timestamp $\le$ the parent token.

4. **Invariant 4 (Budget Non-Exceedance):**
   Cumulative token, monetary, and wall-clock resource consumption MUST NOT exceed the bounds defined in the mission envelope $B$. When any budget threshold is reached, the runtime MUST halt action execution and transition to `NEEDS_INPUT`.

5. **Invariant 5 (State Mutation Traceability):**
   Every state transition and capability execution MUST append an immutable, causally ordered event to trajectory $T$, compatible with OpenTelemetry GenAI semantic conventions.

---

## 3. Lifecycle State Machine

A conforming implementation MUST implement the following 12 discrete states:
- `DRAFT`: Contract composition; schema validation pending.
- `READY`: Contract valid against JSON Schema; awaiting delegation grant.
- `AUTHORIZED`: Principal has issued a valid, signed delegation token.
- `RUNNING`: Active tool invocation loop.
- `PAUSED`: Suspended by operator intervention.
- `NEEDS_INPUT`: Halted due to budget limit, policy tripwire, or unresolvable ambiguity.
- `VERIFYING`: Agent execution concluded; independent verifiers executing.
- `VERIFIED`: Ground truth satisfied by qualifying Tier 2/3 evidence.
- `RECOVERING`: Automated retry with diagnostic feedback following verification rejection.
- `FAILED`: Terminal failure; recovery limit exhausted or unrecoverable error.
- `CANCELLED`: Aborted by authorized human operator.
- `REVOKED`: Terminated due to credential or token invalidation.

---

## 4. Contract Wire Formats (JSON Schema Draft 2020-12)

Missions MUST be serialized conforming to the canonical schema:
- Schema URI: `https://intelligence.systems/schemas/v0alpha1/mission.json`
- Media Type: `application/vnd.intelligence-system.mission+yaml` or `+json`

---

## 5. Attenuated Delegation Token

Authority grants MUST be modeled as portable delegation tokens conforming to RFC 8693:
```yaml
delegation:
  id: "del-uuid"
  principal: "urn:principal:human:id"
  delegate: "urn:agent:id"
  purpose: "urn:mission:id:v1"
  scope:
    allowed_capabilities: ["mcp://*"]
    denied_capabilities: ["mcp://aws/iam:*"]
  budget:
    max_usd: 10.0
    max_tokens: 50000
  valid_from: "2026-09-03T20:00:00Z"
  expires_at: "2026-09-03T23:00:00Z"
  allow_redelegation: true
  max_delegation_depth: 2
```

---

## 6. Progressive Disclosure Context Bounds

To prevent model context thrashing, conforming runtimes MUST enforce a progressive disclosure hierarchy:
- **Tier 1 (Execution Payload):** Injected into the model prompt. MUST NOT exceed 500 tokens.
- **Tier 2 (Verification Payload):** Acceptance criteria and test scripts MUST be retained out-of-band by the verifier engine and withheld from the agent planning context.
- **Tier 3 (Audit Payload):** Trajectory events MUST be emitted out-of-band to telemetry storage.

---

## 7. Security and Privacy Considerations

1. **Goal Hijack Resistance:** Mission objectives are immutable once authorized. Untrusted tool outputs cannot alter the mission contract.
2. **Confused Deputy Mitigation:** Purpose-bound token attenuation blocks rogue subagents from accessing ambient cloud infrastructure.
3. **Data Redaction:** Trajectory loggers MUST redact PII and credentials prior to emitting spans.

---

## 8. IANA Considerations

This document requests registration of the Uniform Resource Name (URN) sub-namespace `urn:mission:*` and `urn:delegation:*` under the IANA URN registry.

---
*End of RFC 0001.*
