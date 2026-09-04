# SPEC-001 Clean-Room Implementation Audit Rubric
**Candidate ID:** `[ASSIGNED_BY_COORDINATOR]`  
**Target Language:** `[Rust / Go / Java / TypeScript / Other]`  
**Implementer Organization / Team:** `[External Independent Engineering Team]`  
**Evaluation Harness:** `conformance/standalone_runner.py (SPEC-001 v0.2)`  

---

## 1. Quantitative Effort & Friction Metrics

| Metric | Target / Benchmark | Actual Value | Notes |
| :--- | :--- | :--- | :--- |
| **Total Engineering Time** | $\le 16$ hours | `___ hours` | Wall-clock hours from package unpack to 14/14 pass |
| **Clarification Questions Raised** | 0 (Self-contained) | `___ questions` | Any question asked of authors regarding spec meaning |
| **Ambiguities Identified** | $\le 2$ | `___ ambiguities` | Items in specification where normative wording was vague |
| **Spec Errata Documented** | As discovered | `___ errata` | Typographical, schema, or logical errors spotted |
| **First-Run Conformance Pass Rate** | $\ge 70.0\%$ | `___ / 14` | Pass count before implementing edge-case bug fixes |
| **Final Conformance Pass Rate** | **14 / 14 (100.0%)**| `___ / 14` | Mandatory gate for Level D candidate qualification |
| **Clean Binary / Memory Size** | Record | `___ MB` | Static executable size or memory RSS at idle |

---

## 2. Qualitative Ambiguity & Errata Log

Please log every section of `SPECIFICATION.md` or `schemas/` that required non-obvious interpretation:

| Ref # | Spec Section / Line | Ambiguity Description | How Implementer Resolved It | Suggested Spec Correction |
| :--- | :--- | :--- | :--- | :--- |
| **A-01** | `Section 3.2 (State Machine)` | *Example: Was CANCELLED reachable from VERIFYING?* | *Assumed CANCELLED allowed from any active state.* | *Add explicit transition tuple.* |
| **A-02** | | | | |
| **A-03** | | | | |

---

## 3. Conformance Verification Checklist

- [ ] **TC-001:** Manifest Schema Conformance (JSON Schema Draft 2020-12)
- [ ] **TC-002:** Mission Contract Schema Conformance
- [ ] **TC-003:** Invariant 1: Non-Equivalence of Complete and Verified
- [ ] **TC-004:** Invariant 2: Evidence-Gated Outcome
- [ ] **TC-005:** Invariant 3: Purpose-Bound Authority Attenuation
- [ ] **TC-006:** Invariant 4: Budget Enforcement
- [ ] **TC-007:** Lifecycle State Machine Progression
- [ ] **TC-008:** OpenTelemetry GenAI Trajectory Event Compliance
- [ ] **TC-009:** Assurance Tier Compliance (Tier 0 Rejection)
- [ ] **TC-010:** Recovery Policy Execution
- [ ] **TC-011:** Delegation Expiration & Mid-flight Revocation
- [ ] **TC-012:** Sub-delegation Monotonic Attenuation
- [ ] **TC-013:** Multi-threaded State & Trajectory Concurrency Invariants
- [ ] **TC-014:** Minimum Assurance Tier Enforcement

---

## 4. Attestation of Independence

I/We hereby certify that:
1. This implementation was developed solely from the documents, schemas, and test vectors provided in `external_validation_pack_vNext/`.
2. No access to the reference implementation (`runtime/`, `agent/`, `architecture/`) or internal project repositories was used during development.
3. All questions and ambiguities have been recorded truthfully above.

**Signed:** `____________________________________`  
**Date:** `____________________`
