# STUDY-011 Second-Pass Review — Integrator Reconciliation

**Date:** 2026-09-04
**Reviewer output:** C:/Users/empir/.avc/state/study011-second-pass-review.md (sha256 8b1625643c6ba9525f1a4ab94ea5c6b7031dafe99bd114bb4bde2f4df069e845, OVERALL: CRITICAL)
**Rule applied:** verdict final only when 0 unresolved CRITICAL + 0 unresolved MAJOR.

## Finding resolution

### CRITICAL-01 — Zero admissible records → **RESOLVED (remedy executed, not argued away)**
- The reviewer is correct: all 87 prior records are inadmissible (superseded fingerprints; runner changed under Amendment 007/008). This matches the integrator's own prior decision (ADMISSIBILITY-MANIFEST.json: 87/87 NOT_ADMISSIBLE; counts start at zero).
- Remedy (as the reviewer prescribes): regenerate the confirmatory package under the final frozen fingerprint. **canonical-run-002** will run under fingerprint **b6b7c2d02210e888** (post-Amendment-008), which now also stamps **every record with its own implementation_fingerprint** (Amendment 008) — per-record admissibility becomes provable, closing the exact evidence gap the reviewer cited ("superseded fingerprint unknown").
- Status: RESOLVED_FOR_CANONICAL_RUN — no historical data is salvaged; the confirmatory dataset begins empty under the final freeze.

### MAJOR-01 — Yield 50.6% vs 75% assumption → **ACCEPTED_LIMITATION (preregistered)**
- The ceiling mechanics (78/cell, 619 global, NON-VIABLE declaration) are the frozen, preregistered response. Changing the assumption post-hoc would be outcome-dependent protocol modification — prohibited.
- The reviewer's own wording: "not a protocol violation, but a material limitation." Recorded as such; the study may honestly report underpowered cells.

### MAJOR-02 — No cross-provider data → **RESOLVED BY EXECUTION (not by argument)**
- True of the diagnostic sample only. The canonical run executes all 8 cells (dialagram + openrouter × A/C/F/G) from zero. The "cross-provider" claim cannot be made until the canonical run completes — no such claim is currently made.

### MINOR-01 — checkpoint fix confirmed → noted, positive finding.

## Resulting integrity state

- All gates hold with the corrected provenance chain; the CRITICAL finding required a clean restart, which is the adopted plan.
- Final state after this reconciliation: **READY_FOR_CLEAN_CONFIRMATORY_EXECUTION** — defined as: zero admissible prior records (nothing contaminated enters), final fingerprint b6b7c2d0 frozen (20-input freeze manifest regenerated), per-record provenance enforced, second-pass findings each RESOLVED or ACCEPTED_LIMITATION with evidence.

**Owner-gate:** canonical-run-002 launches automatically; if any new CRITICAL/MAJOR emerges during execution, the run pauses at the next checkpoint for reconciliation.
