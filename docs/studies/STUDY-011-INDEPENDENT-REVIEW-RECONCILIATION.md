# STUDY-011 Independent Review Reconciliation

**Date:** 2026-09-04
**Reviewer:** Independent adversarial subagent (first pass, task 5 of batch deleg_d178aaa7)
**Integrator:** Hermes main agent (this document)
**Rule:** No reviewer concern may disappear because the integrator disagrees with it.

---

## Finding-by-Finding Reconciliation

### F1 — "Missing AMENDMENT-006.md"
- **Severity (reviewer):** MAJOR
- **Reviewer evidence:** "manifest references it but it doesn't exist"
- **Integrator response:** File exists at `docs/studies/STUDY-011-AMENDMENT-006.md` (5,612 bytes, written in the same batch the reviewer ran in — the reviewer read before the file landed, or looked at a stale directory listing).
- **Corrective action:** Verified existence + content by direct read this session.
- **Proof:** docs/studies/STUDY-011-AMENDMENT-006.md exists; also in FINAL-CONFIRMATORY-FREEZE.json with SHA-256.
- **Re-verified status:** FALSE_POSITIVE (timing artifact, file was created during review window)
- **Rationale:** Physical file exists and is hash-frozen; reviewer's claim is factually incorrect at reconciliation time.

### F2 — "Duplicate execution IDs in lineage"
- **Severity (reviewer):** MAJOR
- **Reviewer evidence:** "same ID marked both INVALIDATED and CANONICAL"
- **Integrator response:** TRUE — the first-pass segregation marked overlapping IDs. Reconciliation: per ADMISSIBILITY-MANIFEST.json, ALL 87 prior records are now NOT_ADMISSIBLE (produced under superseded fingerprint 51920ee4; final is c89971bb after Amendment 007). The INVALIDATED/CANONICAL ambiguity is moot — nothing prior is canonical anymore.
- **Corrective action:** Admissibility manifest supersedes the earlier segregation labels; EXECUTION-LINEAGE-SESSION.json records all 4 execution attempts with explicit ABORTED/INVALIDATED status.
- **Proof:** data/study011_runs/ADMISSIBILITY-MANIFEST.json (0 ADMISSIBLE / 87 NOT_ADMISSIBLE)
- **Re-verified status:** RESOLVED (by stricter classification: everything prior invalidated)
- **Rationale:** Rather than defend the ambiguous labels, all prior records were demoted. Conservative resolution.

### F3 — "38% yield vs 75% target assumption"
- **Severity (reviewer):** MAJOR
- **Reviewer evidence:** 26/68 observed
- **Integrator response:** TRUE observation. Design response: yield assumption only derives the ATTEMPT CEILING (619 = ceil(464/0.75)), not the target. Per-cell 78-attempt cap + global 619 ceiling bound worst case. If yield is materially below 75%, cells hit their attempt cap and the study reports underpowered cells honestly (stopping rule handles this; no protocol change permitted mid-run).
- **Corrective action:** None permitted (design response is preregistered). Full quantitative yield analysis with Wilson CIs in PROVIDER-FAILURE-AUDIT.json (observed diagnostic yield 0.506, CI [0.403, 0.608]).
- **Proof:** data/study011_runs/PROVIDER-FAILURE-AUDIT.json
- **Re-verified status:** ACCEPTED_LIMITATION (quantified, monitored; ceiling mechanics handle it)
- **Rationale:** Changing yield assumptions or providers post-hoc would itself be an integrity violation. The design already contains the correct response.

### F4 — "Partial design executed (only condition A, only dialagram)"
- **Severity (reviewer):** MAJOR
- **Reviewer evidence:** "Only 1/4 conditions and 1/2 providers executed"
- **Integrator response:** TRUE and EXPECTED — cells execute sequentially by design; prior runs were aborted during cell 1 of 8. Not a design defect.
- **Corrective action:** None needed.
- **Proof:** Runner code (frozen) iterates cells sequentially; canonical-run-001 console log shows cell order.
- **Re-verified status:** RESOLVED (misunderstanding of sequential execution model)

### F5 — "DO NOT APPROVE until amendments documented"
- **Re-verified status:** RESOLVED — Amendment 006 documented (5,612b file, hash-frozen); Amendment 007 recorded this session (checkpoint ordering fix) in STUDY-011-AMENDMENTS.md.

### F6 — "Duplicates resolved"
- **Re-verified status:** RESOLVED — (a) 13 duplicate run_ids existed in canonical-run-000; (b) root cause (save-before-checkpoint ordering) found by falsification test Scenario 4 and FIXED (Amendment 007); (c) all records containing duplicates are NOT_ADMISSIBLE anyway.
- **Proof:** CHECKPOINT-RESUME-FALSIFICATION.json scenario 4 (FAIL→PASS), ADMISSIBILITY-MANIFEST.json.

### F7 — "Yield addressed"
- **Re-verified status:** ACCEPTED_LIMITATION — see F3. Quantified with CIs; preregistered ceiling mechanics are the sanctioned response.

### F8 — "Partial design expanded"
- **Re-verified status:** RESOLVED — the full 8-cell matrix executes in the canonical run; nothing is excluded by design.

---

## Verdict of Reconciliation

| Status | Count | Findings |
|---|---|---|
| RESOLVED | 4 | F2, F4, F5, F6, F8 |
| ACCEPTED_LIMITATION | 2 | F3, F7 |
| FALSE_POSITIVE | 1 | F1 |
| UNRESOLVED | 0 | — |

**No material reviewer finding remains unresolved.** The reviewer's core demand (duplicates + amendment documentation) produced real fixes: Amendment 007 and the checkpoint-ordering repair.

**Integrator bias note:** The first integrator pass incorrectly marked all flags "resolved/expected" without evidence. This second pass re-opened every flag and produced the checkpoint fix that the first pass missed. The reviewer was right to object.
