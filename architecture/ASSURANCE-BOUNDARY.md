# Assurance Boundary Specification
**Document:** `ARCH-ASSURANCE-BOUNDARY-001`  
**Governing Standard:** SPEC-001  

---

## 1. The Core Firewall: Complete $\neq$ Verified

The **Assurance Boundary** is the cryptographic and logic firewall prohibiting an AI agent from verifying its own work.

$$\text{Complete}(M) \not\implies \text{Verified}(M)$$

In traditional agent engineering, the agent model serves as actor, judge, and verifier simultaneously. This single point of failure produces the 84.7% False Completion Rate observed in complex benchmarks.

The Assurance Boundary physically isolates verification:
1. **The Actor (In-House Agent):** Proposes candidate solutions.
2. **The Verifier (Assurance Engine):** Evaluates ground truth out-of-band.

---

## 2. Evidence Tier Invariants

The Assurance Boundary enforces strict tier segregation:

### Tier 0: Agent Self-Assertion (Strictly Prohibited for State Finalization)
- **Examples:** `"All tests pass"`, `"I have deployed the update"`, `"Task complete"`.
- **System Rule:** Tier 0 assertions have an assurance weight of zero ($W=0.0$). Any attempt to use a Tier 0 item to satisfy a success criterion is rejected with an `AssuranceTierViolation`.

### Tier 1: Model-Assisted Evaluation (LLM-as-a-Judge)
- **Usage:** Subjective evaluations (e.g., code readability, tone analysis, semantic similarity).
- **Limitation:** Susceptible to agreement bias and false positives. Allowed only when mission explicitly declares $\theta = \text{Tier 1}$.

### Tier 2: Deterministic Test Receipts (Mandatory for Systems Tasks)
- **Examples:** Unit test runner output (`pytest exit=0`), compiler exit code (`cargo build exit=0`), static linter outputs, Prometheus metric thresholds.
- **Requirement:** Must include exact command, exit code, stdout/stderr hash, and timestamp.

### Tier 3: Cryptographic Attestation (High-Assurance / Financial)
- **Examples:** Hardware-backed TPM/TEE measurements, signed C2PA provenance manifests, third-party webhook signatures (Ed25519), transparency log entry (Rekor).

---

## 3. The Recovery Mechanism

When the Assurance Loop detects a criterion failure during `VERIFYING`:
1. It records an `ASSURANCE_FAILED` event in the trajectory.
2. It transitions the state to `RECOVERING`.
3. It compiles an actionable, structured diagnostic payload containing the exact verifier failure (e.g., test failure trace, syntax error line).
4. It deducts one recovery attempt from the mission recovery allowance.
5. It returns control to the In-House Agent Execution Loop with the diagnostic payload appended as a system feedback prompt.
6. If the recovery budget is exhausted ($R \le 0$), it transitions to `FAILED` or alerts the human operator via `NEEDS_INPUT`.
