# STUDY-011 Amendment 006: Protocol Fixes & Neutrality Review

**Date:** 2026-09-04  
**Amendment ID:** AMENDMENT-006  
**Status:** LIVE (pre-data, frozen)

---

## Summary

This amendment documents two protocol fixes identified during baseline verification of STUDY-011:

1. **LIVE_PROTOCOL_FAILURE classification** — proper handling of condition-isolation violations
2. **latency_ms provenance requirement** — explicit validation that latency_ms > 0

Both fixes are **protocol-compliant** and do not alter hypotheses, conditions, sample-size requirements, stopping rules, classification logic, or analysis methods. They tighten provenance requirements to match the pre-registered LIVE_ONLY invariant.

---

## Fix 1: LIVE_PROTOCOL_FAILURE Classification

### What Changed

In `experiments/live_benchmark/study011_analyze.py`, the `classify_execution()` function properly routes records to `LIVE_PROTOCOL_FAILURE` when:

1. **Assurance invocation mismatch:**
   - Condition F or G without assurance invoked (`assurance_invoked=False`)
   - Condition A or C with assurance invoked (`assurance_invoked=True`)
2. **Mission failure despite HTTP 200:**
   - `mission_state_final` is ERROR or TIMEOUT with `http_status=200`

### Why This Fix

Prior to this fix, records with structural protocol violations were not being distinguished from `LIVE_VALID` or `LIVE_PROVIDER_FAILURE`. The classification taxonomy now aligns with pre-registered A12:

| Classification | Criteria |
|---------------|----------|
| LIVE_VALID | http_status=200, complete provenance, no condition-isolation violation |
| LIVE_PROVIDER_FAILURE | http_status≠200 (transport failure, rate-limit, timeout) |
| LIVE_PROTOCOL_FAILURE | http_status=200, provenance complete, but condition-isolation or mission-state violation |
| INVALID_PROTOCOL | Missing provenance fields (request_id, hashes, token counts, latency_ms>0) |
| EXCLUDED | Non-confirmatory conditions |

### Neutrality Impact

**None.** This fix does not affect:
- **Hypotheses:** H1, H2, H3 remain unchanged
- **Conditions:** A, C, F, G remain unchanged
- **Sample-size requirements:** 464 LIVE_VALID minimum still required
- **Stopping rules:** Per-cell 58 LIVE_VALID minimum still applies
- **Classification:** LIVE_PROTOCOL_FAILURE records are correctly excluded from confirmatory analysis per pre-registered A12
- **Analysis:** Paired McNemar tests still run on LIVE_VALID records only

**Prior observations remain admissible** — records classified as LIVE_PROTOCOL_FAILURE were already correctly excluded from confirmatory analysis (they would have been counted as EXCLUDED or invalid under the previous ambiguous classification).

---

## Fix 2: latency_ms Provenance Requirement

### What Changed

In `experiments/live_benchmark/run_study_011.py` (lines 100-101) and `study011_analyze.py` (lines 449-454):

```python
if self.latency_ms <= 0:
    issues.append("latency_ms must be > 0")
```

A record with `latency_ms <= 0` or missing `latency_ms` is now classified as `INVALID_PROTOCOL` rather than `LIVE_VALID`.

### Why This Fix

Latency is a core provenance field indicating a genuine attempt occurred. A value of 0 or missing suggests:
- The request was not actually sent
- The response was cached/simulated
- A data corruption issue

This fix enforces the pre-registered LIVE_ONLY invariant: every confirmatory record must represent a genuine remote API call.

### Neutrality Impact

**None.** This fix does not affect:
- **Hypotheses:** No change to H1/H2/H3
- **Conditions:** No change to A/C/F/G logic
- **Sample-size requirements:** Still 464 LIVE_VALID minimum (latency_ms<=0 records are excluded, not counted as LIVE_VALID)
- **Stopping rules:** Unchanged
- **Classification:** latency_ms<=0 records are correctly excluded via INVALID_PROTOCOL
- **Analysis:** Primary analyses (VSR, FCR, CPVO) exclude LIVE_INVALID records anyway; this simply makes the exclusion criterion explicit

**Prior observations remain admissible** — any records with latency_ms<=0 were already excluded from confirmatory analysis (they were either missing from datasets or counted as invalid under the previous incomplete validation).

---

## Overall Neutrality Assessment

| Aspect | Impact | Rationale |
|--------|--------|-----------|
| Hypotheses | None | H1/H2/H3 unchanged |
| Conditions | None | A/C/F/G behavior unchanged |
| Sample Size | None | LIVE_VALID minimum unchanged; fixes exclude invalid records |
| Stopping Rules | None | Per-cell 58 LIVE_VALID unchanged |
| Classification | Strengthened | LIVE_PROTOCOL_FAILURE now explicit category |
| Analysis | None | McNemar/Wilson/Cohen's h unchanged |
| Prior Admissibility | Affirmative | All LIVE_VALID records remain valid; invalid records properly excluded |

---

## Observations Before Fixes

Prior to these fixes:
- Some records with assurance violations may have been misclassified
- Records with latency_ms=0 or missing latency_ms were not explicitly validated
- The INVALID_PROTOCOL category existed but validation was incomplete

After fixes:
- All 5-class taxonomy (LIVE_VALID, LIVE_PROVIDER_FAILURE, LIVE_PROTOCOL_FAILURE, INVALID_PROTOCOL, EXCLUDED) is fully implemented
- Validation is complete and matches pre-registered A12

---

## Conclusion

Both fixes **strengthen protocol compliance** without altering inferential requirements. The amendments are **neutral** with respect to STUDY-011 hypotheses and analysis plan. No prior confirmatory observations are invalidated.

---

**Amendment Author:** Automated Baseline Verification (STUDY-011 Gate G3+G4)
**Review Status:** Pending Owner Approval
