# External Blind Implementation Rules and Conformance Rubric
**Specification Target:** `SPEC-001-MISSION-CONTRACT-v0.1-FROZEN`  
**Challenge Coordinator:** Jonas Abde Research Program  
**Track:** Phase EXT-3A (Independent Clean-Room Reproduction)  

---

## 1. Ground Rules for External Implementers

To achieve true Level D standard-candidate maturity, an independent team must implement the specification purely from documentation:

1. **Information Isolation (Clean-Room Firewall):**
   - The implementing team shall have access ONLY to:
     - `SPECIFICATION.md` (normative spec)
     - `schemas/*.json` (JSON Schemas Draft 2020-12)
     - `test_vectors/*.json` (standardized mission and delegation payloads)
     - `conformance/test_cases.json` (acceptance criteria)
     - `conformance/standalone_runner.py` (black-box conformance harness)
   - The implementing team shall NOT inspect:
     - `runtime/engine.py` (Python reference implementation)
     - `validation/independent_runtime.py` (second in-tree implementation)
     - `external_validation_pack/implementations/` (in-tree Node.js engine)
     - Private developer chat logs, commit messages, or direct consultation from Jonas Abde.

2. **Language Choice:**
   - Implementers are strongly encouraged to implement in a distinct programming language (e.g., **Rust, Go, Java, C#, or Swift**) to test platform-agnostic portability.

---

## 2. Quantitative Evaluation Rubric

Every external implementation submission will be scored against the following 8 metrics:

| Metric ID | Metric Name | Definition / Measurement Formula | Target Threshold |
| :--- | :--- | :--- | :--- |
| **M-01** | **Implementation Effort** | Total person-hours from receiving the pack to passing TC-001 through TC-014. | $\le 40$ person-hours |
| **M-02** | **Ambiguities Discovered** | Number of specification sections requiring clarification or reported as underspecified. | $\le 3$ items |
| **M-03** | **Questions Required** | Number of formal RFC-style questions submitted to the coordinator. | $\le 5$ inquiries |
| **M-04** | **Conformance Score** | Percentage of the 14 normative test cases passed on first automated evaluation run. | $100.0\%$ (14/14) |
| **M-05** | **Semantic Deviation** | Number of state machine transitions or invariant evaluations diverging from SPEC-001. | $0$ deviations |
| **M-06** | **Interoperability Failures** | Failures observed when exchanging serialized missions/delegations with the reference runtime. | $0$ failures |
| **M-07** | **Code Complexity** | Lines of code (LOC) required for the core state machine, schema validator, and verifier. | $\le 800$ LOC |
| **M-08** | **Normative Spec Changes** | Number of errata or textual modifications required in SPEC-001 to resolve defects. | Logged in Errata |

---

## 3. Ambiguity & Question Log Template

When an external implementer encounters an ambiguity, they must record it in the following structured format:

```markdown
### Ambiguity Inquiry [ID: AMB-EXT-001]
- **Date:** YYYY-MM-DD
- **Spec Section:** e.g., SPEC-001 § 4.3 (Authority Attenuation)
- **Problem Statement:** What is ambiguous or conflicting?
- **Implementer's Interpretation:** How was it resolved in your code?
- **Proposed Normative Clarification:** Suggested specification diff.
```

---

## 4. Packaging and Delivery Command

To generate a clean, unpolluted distribution ZIP for an external team containing only the frozen specification and test harness:
```bash
python external_validation_pack/package_external_bundle.py
```
Outputs: `dist/SPEC-001-EXTERNAL-VALIDATION-BUNDLE.zip`.
