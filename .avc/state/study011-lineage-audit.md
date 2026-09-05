# STUDY-011 Lineage/Dedupe Audit

**Date:** 2026-09-04  
**Commit:** 5cf5d29  
**Scope:** Verify canonical dataset lineage, dedupe logic, and accounting against amendment docs

---

## Executive Summary

**Verdict: FAIL**

The canonical dataset (`data/study011_runs/confirmatory/canonical-run-002-deduped/run_records.jsonl`) contains structural problems that violate the stated dedupe rules and amendment invariants.

---

## 1. Raw Record Recount & Dedupe Verification

| Metric | Claimed | Verified |
|--------|---------|----------|
| Raw records | 723 | ✅ 723 (canonical-run-002/run_records.jsonl) |
| Raw unique run_ids | 480 | ✅ 480 |
| Duplicate run_ids | 243 | ✅ 243 (480 unique - 237 deduped) |
| Canonical records | 470 | ✅ 470 |
| Canonical unique run_ids | 470 | ✅ 470 |

**Dedupe outcome:** 723 → 470 (253 PROVIDER_FAILURE records removed)

---

## 2. Fingerprint Preference Verification

**Claimed rule:** Prefer `implementation_fingerprint` starting with `dfe3513c` (Amendment 010 paid models), then LIVE_VALID.

**Actual canonical fingerprint distribution:**

| Fingerprint | Records | Conditions |
|-------------|---------|------------|
| b6b7c2d0 | 233 | A, C, F, G |
| dfe3513c | 128 | A, C, G |
| 17bc1037 | 108 | A, C, F, G |
| 0c588022 | 1 | G |

**Violation:** The canonical contains **4 fingerprints** in a single dataset. The dfe3513c fingerprint (Amendment 010) appears in G (22 records) and is NOT exclusively preferred over b6b7c2d0 in A/C/F/G.

---

## 3. Amendment-010 Fingerprint Justification

From `docs/studies/STUDY-011-AMENDMENT-010-INTEGRITY-BOUNDARY.md`:

> **BLOCK 3: POST-AMENDMENT-010 (PAID MODELS)**  
> **Analysis status: EXPLICIT SEPARATE ANALYSIS REQUIRED.** These observations were produced under a different model tier (paid vs free), a different ceiling (931 vs 619), and a different fingerprint. They CANNOT be pooled with Block 1 for inferential purposes unless a pre-specified statistical justification is added to the preregistration via a formal amendment.

**22 Amendment 010 violations found:**
- 22 records with fingerprint `dfe3513c` appear in cells F and G, which should have 0 records per Amendment 010.

---

## 4. LIVE_VALID vs Cell Target Accounting

**Claimed:** 8 cells × 58 = 464 LIVE_VALID target

**Actual canonical-002-deduped:**

| Cell | LIVE_VALID |
|------|------------|
| A | 117 |
| C | 118 |
| F | 116 |
| G | 119 |
| **Total** | **470** |

**Accounting fails:**
- Only 4 conditions exist (A, C, F, G), not 8 cells
- 470 ≠ 464 target (6 extra records)
- Per-fingerprint breakdown shows mixing:

| Fingerprint | A | C | F | G |
|-------------|---|---|---|---|
| b6b7c2d0 | 58 | 59 | 58 | 58 |
| dfe3513c | 58 | 48 | 0 | 22 |
| 17bc1037 | 1 | 11 | 58 | 38 |
| 0c588022 | 0 | 0 | 0 | 1 |

---

## 5. Flagged Observations

| Issue Class | Count | Details |
|-------------|-------|---------|
| **In-flight-at-stop** | 1 | Record 59+ in one cell (fingerprint boundary crossing) |
| **Cross-fingerprint contamination** | 4 cells | All cells (A, C, F, G) contain multiple fingerprints |
| **Amendment 010 violations** | 22 | dfe3513c records in cells F/G (should be separate block) |
| **Block pooling violations** | Multiple | Block 1 (dialagram) and Block 3 (Amendment 010) records mixed |

---

## 6. Specific Findings

### 6.1 In-flight-at-stop (Cell C)
- Amendment 010 documents Cell C having 59th record as IN_FLIGHT_AT_STOP (58th and 59th valids 35s apart, same continuous run, same fingerprint b6b7c2d0)
- Canonical contains both records (59 LIVE_VALID in C)

### 6.2 Cross-lineage contamination
- Cell G contains records from 4 different fingerprints
- Cells A, C, F contain 2-3 different fingerprints
- Amendment 010 requires blocks to be non-poolable

### 6.3 In-flight-at-stop that should be excluded
- The canonical contains 470 records where the accounting expects 464
- 6 extra records cannot be explained by the amendment documentation

---

## 7. Conclusion

**Verdict: FAIL**

The canonical dataset:
1. **Violates Amendment 010** by pooling Block 1 and Block 3 records
2. **Fails the dfe3513c preference rule** - fingerprint is not exclusively preferred
3. **Contains cross-fingerprint contamination** in all 4 cells
4. **Has unexplained accounting** (470 vs 464)

### Recommendations
- Separate Block 1 (dialagram, b6b7c2d0) from Block 3 (Amendment 010, dfe3513c)
- Remove in-flight-at-stop record from Cell C
- Add formal amendment if pooling is required for inferential analysis
- Verify the 6 extra records and their provenance
