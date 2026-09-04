# Provisional Specification Audit & Enablement Review
**Document:** `06_PROVISIONAL_SPECIFICATION_AUDIT.md`  
**Classification:** `ATTORNEY-CLIENT PRIVILEGED & CONFIDENTIAL`  

---

## 1. Statutory Requirements for US Provisional Applications (35 U.S.C. § 111(b))

Patent counsel should note the following procedural and substantive boundaries:

1. **Enablement and Written Description (35 U.S.C. § 112(a)):**
   - A provisional application must contain a written description of the invention in full, clear, concise, and exact terms to enable any person skilled in the art of distributed software systems and artificial intelligence to make and use the same without undue experimentation.
   - The included reference implementation (`runtime/engine.py`), schemas (`schemas/`), and multi-domain test vectors provide literal source-level enablement.

2. **Claims Requirement:**
   - Under 35 U.S.C. § 111(b)(2), formal patent claims are **not required** in a US provisional application.
   - However, **20 preliminary claims** (comprising 3 independent system, method, and computer-readable medium claims) are included in this draft to assist counsel in establishing priority scope and evaluating foreign filing license requirements (e.g., for PCT conversion).

3. **Entity Status and Statutory Fees:**
   - The provisional application fee schedule (FY 2026) is:
     - Large Entity (Undiscounted): \$320 USD
     - Small Entity (60% discount under 35 U.S.C. § 41(h)): \$128 USD
     - Micro-Entity (80% discount under 35 U.S.C. § 123): \$64 USD
   - *Audit Note:* Micro-entity status requires certifying that the inventor has not been named on more than 4 previously filed non-provisional patent applications and has a gross income below 3x the median household income. Patent counsel must verify eligibility prior to fee remittance.

4. **Prohibition of "Patent Pending" Claims Prior to Receipt:**
   - Under 35 U.S.C. § 292, it is a statutory offense to falsely mark an invention as "Patent Pending" or "Patent Applied For" without an active application on file.
   - **Mandatory Directive:** The research program shall strictly maintain a `PRIVATE_PENDING_IP_REVIEW` status and shall NOT advertise or claim "Patent Pending" until an official **USPTO Filing Receipt** displaying an assigned **Application Serial Number (e.g., 63/xxx,xxx)** is issued.

---

## 2. Summary of Preliminary Claims Included in Specification Draft

- **Claim 1 (Independent Method):** A computer-implemented method for autonomous agent lifecycle control, comprising loading an immutable mission contract, executing actions within a purpose-bound delegation grant, intercepting an agent completion signal, preventing direct transition to a verified outcome, initiating out-of-band deterministic verifiers, and transitioning to a terminal verified state only upon cryptographically validating Tier 2/Tier 3 evidence receipts.
- **Claims 2–8 (Dependent Claims):** Requisite assurance tiers, monotonic authority attenuation, automatic delegation depth decrements, mid-flight revocation cascades, hard budget token/cost containment, and progressive disclosure prompt injection.
- **Claim 9 (Independent System):** An autonomous agent execution runtime system comprising memory storing an execution state machine, a policy engine, a verifier engine, and processors configured to enforce Invariants 1–5.
- **Claims 10–18 (Dependent Claims):** Multi-tenant capability routing, SHA-256 event chaining, external signed checkpoint anchoring, and automatic recovery state transitions.
- **Claim 19 (Independent Non-Transitory Storage Medium):** Computer-executable instructions for causing distributed processors to enforce the evidence-gated interception lifecycle.
- **Claim 20 (Dependent Medium Claim):** Instructions for validating cryptographic evidence receipts against declared mission criteria.
