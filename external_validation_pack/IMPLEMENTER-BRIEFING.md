# Independent Implementer Briefing
## STUDY-013 G-13a Recruitment

**Status:** APPROVED-ACTIVE  
**Prepared:** 2026-09-04

---

## What You Build

A clean-room implementation of the **SPEC-001 Intelligence System Contract** specification. You will build a runtime that:

1. Parses and validates mission contracts against the provided JSON schemas
2. Enforces the 8 lifecycle states (DRAFT → READY → AUTHORIZED → RUNNING → VERIFYING → VERIFIED/FAILED)
3. Handles delegated authority with proper attenuation
4. Blocks unauthorised actions before execution
5. Requires evidence before transitioning to VERIFIED state
6. Produces a machine-readable conformance report

---

## What You Receive

You will receive exactly these files (SHA-256 hashes provided in the manifest):

- `SPECIFICATION.md` - Full normative specification
- `BLINDED_INTEROPERABILITY_CHALLENGE.md` - Challenge protocol
- `schemas/mission.v0alpha1.json` - Mission contract schema
- `schemas/delegation.v0alpha1.json` - Delegation token schema
- `schemas/evidence.v0alpha1.json` - Evidence receipt schema
- `test_vectors/` - Sample inputs for testing
- `conformance/standalone_runner.py` - Self-contained test harness

**You will NOT receive:**
- Reference implementation source code
- Internal architecture notes
- Design intent beyond the written specification

---

## Time-Box

**Expected completion:** 4–8 weeks from materials receipt

Track your implementation:
- Start date/time
- Hours spent per week
- First pass/fail date for each conformance test

This timeline is part of the research data.

---

## Logging Requirements

You must submit:

| File | Contents |
|------|----------|
| `ambiguity_log.csv` | Questions about specification clarity |
| `errata_log.csv` | Any specification errors or gaps found |
| `conformance_results.json` | Output from `standalone_runner.py` |
| `implementation_time_hours.txt` | Total clock hours spent |

All ambiguity questions are valuable data. Do not work around unclear sections silently.

---

## No-Coaching Rule

You must not:
- Request clarifications from project authors beyond the written specification
- Share implementation details with other implementers (if multiple teams participate)
- Access any internal or reference implementation code
- Use other implementers' solutions

If you accidentally encounter reference code, disclose it. Your implementation will be excluded from the independence dataset but your experience notes remain valuable.

---

## Compensation

This is a **research reproducibility exercise**, not a commercial engagement:

- **No direct compensation** for implementation time
- **Authorship consideration** in the published research report (optional)
- **Public recognition** for successful independent conformance
- Your timeline and ambiguity data contribute to the published evidence

---

## Submission Requirements

```
submission/
  independence_declaration.md    (signed)
  implementation_language.txt    (e.g., "Rust 1.78")
  implementation_time_hours.txt
  ambiguity_log.csv
  errata_log.csv
  conformance_results.json
  README.md
  source/
```

---

## Next Steps

1. Review `SPECIFICATION.md` and confirm you can implement from it
2. Sign the independence declaration
3. Receive materials package
4. Begin implementation

**Questions about the briefing itself may be asked to the study coordinator. Questions about specification implementation intent must be logged via the ambiguity_log.csv template.**
