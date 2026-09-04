# Standards Overlap and Defensive Analysis
**Document:** `05_STANDARDS_OVERLAP_AND_DEFENSIVE_ANALYSIS.md`  
**Classification:** `ATTORNEY-CLIENT PRIVILEGED & CONFIDENTIAL`  

---

## 1. RFC 8693 (OAuth 2.0 Token Exchange) vs. Present Invention

### RFC 8693 Scope:
RFC 8693 defines an HTTP POST protocol where a client requests a security token from an authorization server by presenting an existing subject token (`subject_token`) and optional actor token (`actor_token`).

### Precise Delineation:
- RFC 8693 is a **transport and message format** for token swaps.
- RFC 8693 **does not define or enforce**:
  1. Monotonic capability attenuation ($\Omega_{\text{sub}} \subseteq \Omega_{\text{parent}}$).
  2. Automatic subdelegation depth decrementing ($d - 1$).
  3. Purpose-binding to an autonomous agent mission URN.
  4. Automatic mid-flight subtree revocation cascades.
- **Defensive Position:** Our specification uses RFC 8693 concepts as an underlying plumbing mechanism where applicable, but the normative rules governing monotonic attenuation and purpose binding are novel programmatic invariants residing in the agent runtime.

---

## 2. OpenTelemetry GenAI Semantic Conventions

### OpenTelemetry Scope:
OpenTelemetry defines semantic attributes for logging LLM interactions (e.g., `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.prompt_tokens`).

### Precise Delineation:
- OpenTelemetry is an observational telemetry protocol (passive logging).
- The present invention integrates OpenTelemetry event naming for transparency, but couples it to an active, cryptographic, tamper-evident SHA-256 hash chain and signed checkpoint ledger that drives state transitions and recovery triggers.

---

## 3. IEEE P3709 and IEEE P3777

### IEEE Standards Scope:
- **IEEE P3709:** Focuses on standardizing execution interfaces, model serving containers, and runtime packaging for AI models.
- **IEEE P3777:** Emerging study group focusing on reliability benchmarks and agent evaluation criteria.

### Defensive Position:
Neither IEEE P3709 nor IEEE P3777 defines a declarative 8-tuple mission contract with an unforgeable interception state machine holding execution in `VERIFYING` against deterministic out-of-band test receipts.

---

## 4. NIST AI 200-2 (AI TEVV Guidelines)

### NIST TEVV Scope:
NIST AI 200-2 provides a conceptual risk management and evaluation framework under the AI Risk Management Framework (AI RMF 1.0).

### Precise Delineation:
NIST provides non-normative policy guidance and evaluation recommendations. The present invention provides the concrete, computer-implemented state machine, cryptographic data schemas, and runtime enforcement algorithms that operationalize NIST TEVV requirements in production multi-agent systems.
