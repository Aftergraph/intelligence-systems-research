# External Implementer Outreach Package
## SPEC-001: Machine-Readable Intelligence Systems Mission Contract
### Independent Blind Implementation Challenge

**Reference:** Jonas Abde Intelligence Systems Research Program Q3 2026  
**Document class:** Outreach only — does NOT contain reference implementation  
**Version:** 0.1-DRAFT  
**Prepared:** 2026-09-04  
**Status:** DRAFT — Not yet transmitted to any external party (IP hold active)

---

## 1. Purpose

We are seeking one or more external engineering teams to independently implement **SPEC-001 version 0.2-FROZEN** from specification alone, without access to our reference implementation or internal architecture.

This is a **research reproducibility exercise**, not a commercial engagement. The goal is to determine:

- Whether the specification is self-contained and unambiguous enough to implement without author assistance.
- Whether an independently built implementation passes the SPEC-001 conformance suite.
- What ambiguities, gaps, or errata emerge during independent implementation.

Results will be recorded in a published research report. Your implementation timeline, questions, and conformance results form part of the evidence dataset.

---

## 2. What You Will Receive

The following materials will be provided to accepted implementers:

| Item | Contents |
|---|---|
| `SPECIFICATION.md` | Full normative text of SPEC-001 v0.2-FROZEN |
| `NORMATIVE_TERMINOLOGY.md` | Defined terms and their precise meanings |
| `schemas/mission.v0alpha1.json` | JSON Schema 2020-12 for the Mission Contract object |
| `schemas/receipt.v0alpha1.json` | JSON Schema for Verification Receipt |
| `test_vectors/` | Normative test vectors (input/expected output pairs) |
| `conformance/standalone_runner.py` | Self-contained conformance test runner |
| `IMPLEMENTATION_RUBRIC.md` | Scoring criteria and measurement protocol |

**Explicitly excluded:**
- Reference implementation source code
- Internal test implementation details
- Architecture implementation notes
- Any code from the program's internal codebase

---

## 3. Rules

1. **No access to reference implementation.** Do not request it. If you accidentally encounter it (e.g., via public repository), you must disclose this and your implementation will be disqualified from the independence dataset (but your experience notes remain valuable).

2. **Language:** Implement in any language except Python 3.11 (the reference implementation language). Preferred: Rust, Go, TypeScript, Java, C#, Kotlin.

3. **Clarifications via structured log only.** Do not ask the program authors for design intent beyond what the specification states. All questions must be submitted via the Ambiguity Log template (Section 7). The existence and content of your questions is itself part of the research data.

4. **Timeline tracking required.** Record the date/time you started, the hours spent, and the date you first passed or failed each conformance test. This implementation timeline is a key data point.

5. **No collaboration between implementers.** If multiple teams participate, they must not share implementation details until both have completed conformance testing and submitted results.

6. **Independence declaration required.** Before receiving materials, sign the Independence Declaration (Section 8).

7. **Errata are expected and valuable.** If the specification is ambiguous or wrong, record it in the Errata Log. Do not work around unclear sections silently.

---

## 4. Allowed Materials

Implementers MAY use:

- The materials listed in Section 2 (only those)
- General AI coding assistants (Copilot, Claude, etc.) for implementation — but not to interpret ambiguous spec language (spec interpretation must come from the text itself)
- Public language documentation, libraries, and tools
- Public JSON Schema validators

Implementers MAY NOT use:

- Any code from the program's GitHub or internal repository
- Author clarifications beyond the written specification
- Other implementers' code

---

## 5. Submission Format

When complete, submit:

```
submission/
  independence_declaration.md    (signed)
  implementation_language.txt    (e.g., "Rust 1.78")
  implementation_time_hours.txt  (total clock hours)
  timeline_log.csv               (date, hours, milestone)
  ambiguity_log.csv              (question, spec section, resolution)
  errata_log.csv                 (issue, spec section, severity)
  conformance_results.json       (output from standalone_runner.py against your implementation)
  README.md                      (how to build and run your implementation)
  source/                        (your implementation source code)
```

---

## 6. Conformance Procedure

1. Implement the SPEC-001 normative requirements as described in `SPECIFICATION.md`.
2. Run `conformance/standalone_runner.py --candidate path/to/your/implementation`.
3. The runner will output a JSON report with pass/fail per test vector.
4. Submit the full JSON report as `conformance_results.json`.

The conformance suite has **14 normative test cases** covering:
- Mission contract parsing and validation
- State machine transitions (PENDING → EXECUTING → VERIFYING → VERIFIED/FAILED/RECOVERING)
- Authority attenuation invariants
- Evidence receipt validation
- Assurance boundary: agent cannot self-verify

A passing implementation must score **14/14** on all normative cases.

---

## 7. Ambiguity Log Template

Create `ambiguity_log.csv` with columns:

```
question_id, spec_section, your_interpretation, alternative_interpretation, resolved_how, time_spent_hours
```

Fill in one row per ambiguous section encountered. Leave `resolved_how` as `"SPEC_TEXT"` if you resolved it purely from the document, or `"ASSUMPTION"` if you made an implementation choice.

---

## 8. Independence Declaration Template

```markdown
# Independence Declaration

I/We confirm that:

1. I/We have not had access to the reference implementation of SPEC-001.
2. I/We have not received oral or written design-intent guidance from the program authors 
   beyond the written specification materials.
3. I/We will not share implementation details with other participating teams 
   before both teams complete conformance testing.
4. I/We understand that my/our questions, timeline, and conformance results 
   will be published in a research report.

Implementer name/team: _______________
Implementation language: _______________
Start date: _______________
Signature: _______________
Date: _______________
```

---

## 9. What Happens With Your Results

- Conformance results and ambiguity/errata logs will be published in a research report assessing SPEC-001 implementability.
- Your implementation timeline and question count will be reported as metrics.
- If you grant permission, your implementation source may be cited as evidence of independent reproducibility.
- No personal/identifying information will be published without your explicit consent.

---

## 10. Contact and Submission

**[PLACEHOLDER — Fill in before transmission]**

- Contact method: TBD (email / secure form / GitHub issue)
- Materials delivery: TBD (secure link, not public repository)
- Expected timeline: 4–8 weeks from materials receipt to conformance submission

---

## 11. IP Notice

SPEC-001 is currently under IP review. The specification materials provided to implementers will be marked as **pre-publication research materials under confidentiality**. Do not publicly share specification content until notified of release.

> [!CAUTION]
> **This document is a DRAFT.** It has not been transmitted to any external party. The IP hold on external transmission is currently active. This document must be reviewed by IP counsel before any external outreach begins.

---

## Document Control

| Field | Value |
|---|---|
| Version | 0.1-DRAFT |
| Created | 2026-09-04 |
| Status | DRAFT — IP hold active, not yet transmitted |
| Related files | `external_validation_pack_vNext/` |
| Supersedes | N/A |
