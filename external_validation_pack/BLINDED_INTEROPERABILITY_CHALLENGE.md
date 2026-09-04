# Jonas Abde Intelligence Systems Research Program
## Blinded Interoperability Challenge (Phase G / External Challenge)

**Challenge Protocol:** `CHALLENGE-BLIND-001`  
**Purpose:** Verify that an external engineering team can implement a fully interoperable runtime from the normative specification `SPECIFICATION.md` without private knowledge, informal communication, or access to the Jonas Abde reference codebase.

---

## The Challenge Requirements

1. **Clean-Room Implementation:**
   - Write your implementation in your preferred programming language (Rust, Go, Python, TypeScript, etc.).
   - Rely strictly on `SPECIFICATION.md` and the JSON schemas in `schemas/`.
2. **Execute the Standardized Missions:**
   - Load `test_vectors/sample_mission.json` and validate against `schemas/mission.v0alpha1.json`.
   - Authorize execution using `test_vectors/sample_delegation.json`.
   - Simulate a tool action `mcp://github/create_pr` under active delegation.
   - Enforce that a denied action `mcp://aws/terminate_instances` is rejected with an authorization failure.
3. **Evidence Gating Verification:**
   - Intercept the agent completion signal.
   - Prove that your runtime holds state in `VERIFYING` and **never** transitions to `VERIFIED` on model self-assertion alone.
   - Load `test_vectors/sample_evidence.json` and verify that only qualifying Tier 2 or Tier 3 evidence satisfies the mission acceptance criteria.
4. **Pass Conformance Runner:**
   - Execute `conformance/standalone_runner.py` and submit your machine-generated `conformance_report.json`.

---
## Submission of Results
External teams may submit their clean-room repository URL and cryptographic conformance hash to `standards@jonasabde.org` for inclusion in the IEEE P3777 Interoperability Matrix.
