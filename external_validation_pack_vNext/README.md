# SPEC-001 External Blind Implementation Package (vNext)
**Standard:** SPEC-001: Machine-Readable Intelligence Systems Mission Contract  
**Version:** `v0.2-FROZEN`  
**Distribution Target:** External Third-Party Clean-Room Implementers (Rust / Go / Java / TypeScript)  
**Security Classification:** Blinded Research Distribution (Zero Internal Source Included)  

---

## 1. Challenge Overview

You are invited to implement an independent, production-grade runtime conforming to **SPEC-001: Machine-Readable Intelligence Systems Mission Contract**.

To ensure true independence and validate the completeness of the normative specification, this package **strictly excludes** all reference implementations, internal source code, and architectural internal notes. If the specification is well-formed, an experienced systems engineer should be able to achieve 100% conformance without contacting the authors for clarification.

### Target Languages
We invite implementations in:
- **Rust** (preferred for systems performance and memory safety)
- **Go** (preferred for cloud-native / Kubernetes orchestration)
- **TypeScript / Node.js** (preferred for developer tooling and MCP ecosystems)
- **Java / Kotlin** (preferred for enterprise data pipelines)

---

## 2. Package Contents

- [`SPECIFICATION.md`](file:///c:/Users/empir/Downloads/Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026/Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026/external_validation_pack_vNext/SPECIFICATION.md): The normative specification defining core types, state machines, invariants, and error codes.
- [`NORMATIVE_TERMINOLOGY.md`](file:///c:/Users/empir/Downloads/Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026/Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026/external_validation_pack_vNext/NORMATIVE_TERMINOLOGY.md): Definitions of strict architectural terms.
- [`IMPLEMENTATION_RUBRIC.md`](file:///c:/Users/empir/Downloads/Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026/Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026/external_validation_pack_vNext/IMPLEMENTATION_RUBRIC.md): The quantitative audit scorecard to record development metrics.
- `schemas/`: Canonical JSON Schemas (Draft 2020-12) for Manifests, Missions, Delegations, and Evidence.
- `test_vectors/`: Concrete JSON payloads illustrating valid and invalid protocol objects.
- `conformance/`: The normative 14-test conformance suite and standalone test runner.

---

## 3. Four Non-Negotiable Invariants

Any conforming implementation MUST strictly enforce:

1. **Invariant 1: Non-Equivalence of Complete and Verified ($S_{\text{COMPLETED}} \neq S_{\text{VERIFIED}}$)**  
   An agent indicating task completion transitions the mission to `VERIFYING`, NEVER directly to `VERIFIED`.
2. **Invariant 2: Evidence-Gated Outcomes**  
   Transition to `VERIFIED` requires at least one valid, unrevoked, unexpired deterministic evidence receipt meeting the criterion's minimum assurance tier. Self-reported claims (Tier 0) MUST be rejected.
3. **Invariant 3: Purpose-Bound Authority Attenuation**  
   Sub-delegated capabilities must be monotonically attenuated ($C_{\text{child}} \subseteq C_{\text{parent}}$). Any attempt to widen scope or change purpose MUST be rejected.
4. **Invariant 4: Budget Governance**  
   Tokens, financial cost, or tool calls exceeding assigned thresholds MUST trigger immediate containment (`CONTAINED_BUDGET_CEILING`) and prevent further side-effects.

---

## 4. Submission & Audit Protocol

1. Record your starting timestamp.
2. Log every question or ambiguity encountered in `IMPLEMENTATION_RUBRIC.md`.
3. Implement the engine and CLI.
4. Run `python conformance/standalone_runner.py --command "<your_engine_binary>"` until 14/14 test cases pass.
5. Record your ending timestamp, total engineering hours, and submit your source code and completed rubric.
