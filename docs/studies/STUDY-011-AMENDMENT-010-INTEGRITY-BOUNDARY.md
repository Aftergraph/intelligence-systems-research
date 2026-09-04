# STUDY-011 Amendment 010 — Integrity Boundary

**Date:** 2026-09-04
**Purpose:** Separate the confirmatory dataset into three non-poolable blocks with explicit provenance, per the owner's directive on reporting semantics.

---

## BLOCK 1: ORIGINAL CONFIRMATORY (dialagram stratum)

| Property | Value |
|----------|-------|
| Cells | dialagram × A, C, F, G |
| Models | deepseek-v4, xiaomi-mimo-2.5, qwen-3.8-max (dialagram.me/router/v1) |
| Fingerprint | `b6b7c2d02210e888` (Amendments 001–008 era) + `0c58802253706a01` (Amendment 009 breaker-path fix) |
| Stopping rule | 58 LIVE_VALID per cell, max 78 attempts per cell |
| Total records | 241 |
| LIVE_VALID | 234 |
| Excluded (provider failures) | 7 |

### Per-cell detail

| Cell | Valid | Attempts | Yield | Status | Extra record analysis |
|------|-------|----------|-------|--------|----------------------|
| A | 58 | 60 | 96.7% | COMPLETE | 0 extras |
| C | **59** | 61 | 96.7% | COMPLETE + 1 extra | **IN_FLIGHT_AT_STOP** — 58th and 59th valids 35s apart, same continuous run, same fingerprint `b6b7c2d0`. Runner dispatched both before the 58th was checkpointed. **Admissible** if frozen rule permits (preregistered rule: "stop when ≥58" — 59 was already in the pipeline). |
| F | 58 | 60 | 96.7% | COMPLETE | 0 extras |
| G | **59** | 60 | 98.3% | COMPLETE + 1 extra | **POST_STOPPING_EXCLUDED** — 58th valid at 10:27Z under fp `b6b7c2d0`; 59th valid at 11:14Z under fp `0c588022` (47 min later, crossed fingerprint boundary after Amendment 009). **NOT admissible** for the original block. |

### Block 1 admissible count
- Cell A: 58 (all admissible)
- Cell C: 58 admissible + 1 IN_FLIGHT_AT_STOP (classification: admissible only if frozen rule permits — the preregistered stopping rule says "stop when ≥58"; record 59 was in flight, not a separate decision)
- Cell F: 58 (all admissible)
- Cell G: 58 admissible + 1 POST_STOPPING_EXCLUDED (different fingerprint, 47-min gap)

**Block 1 inferential LIVE_VALID: 232** (58×4, excluding both extras from inferential count)

---

## BLOCK 2: ORIGINAL OPENROUTER FREE (NON-VIABLE)

| Property | Value |
|----------|-------|
| Cells | openrouter × A, C, F, G |
| Models | `google/gemma-4-31b-it:free`, `z-ai/glm-5.2:free` (via openrouter.ai) |
| Fingerprint | `0c58802253706a01` |
| Status | **NON-VIABLE** — 100% provider failure (HTTP 429 quota exhaustion) |
| Total records | 238 |
| LIVE_VALID | **0** |
| Provider failures | 238 (all HTTP 429 after 3 retries) |
| Root cause | `:free` tier has a hard daily quota (1000 req/day shared), not a probabilistic failure rate |

**No pooling with Amendment 010.** These 238 records are environmental interruptions, not observations. They do not count toward any LIVE_VALID target, cell count, or stopping rule.

---

## BLOCK 3: POST-AMENDMENT-010 (PAID MODELS)

| Property | Value |
|----------|-------|
| Cells | openrouter × A, C, F, G |
| Models | `google/gemma-4-31b-it` (paid), `z-ai/glm-5.2` (paid) |
| Fingerprint | `dfe3513c72c5d8d6` |
| Ceiling | 931 global / 156 per cell (openrouter) |
| Total records | 107 |
| LIVE_VALID | 106 |
| Excluded | 1 |
| Yield | 99.1% |
| Owner approval | Telegram, 2026-09-04 (Amendment 010 ACTIVE) |

### Per-cell breakdown (openrouter paid)

| Cell | Valid | Model breakdown |
|------|-------|-----------------|
| A | 58 | gemma-4-31b-it: 39, glm-5.2: 19 |
| C | 48 | gemma-4-31b-it: 32, glm-5.2: 16 |
| F | 0 | — |
| G | 0 | — |

**Analysis status: EXPLICIT SEPARATE ANALYSIS REQUIRED.** These observations were produced under a different model tier (paid vs free), a different ceiling (931 vs 619), and a different fingerprint. They CANNOT be pooled with Block 1 for inferential purposes unless a pre-specified statistical justification is added to the preregistration via a formal amendment.

---

## Hard invariant

**Once a cell's valid_count reaches 58, no later record from that cell may affect the inferential valid_count for the ORIGINAL CONFIRMATORY BLOCK.** Records 59+ are classified as IN_FLIGHT_AT_STOP or POST_STOPPING_EXCLUDED and tracked separately.

---

## Openrouter free-block duplicates (watchdog incident)

3 duplicate run_ids found across blocks:
- `study011-dialagram-C-S11-DATA-04-r001`: pair = PROVIDER_FAILURE (b6b7c2d0) + LIVE_VALID (b6b7c2d0). The failure was a pre-request bookkeeping entry; the LIVE_VALID is the real observation. Only the LIVE_VALID counts.
- `study011-openrouter-A-S11-AUTH-01-r001` and `-r002`: both pairs are PROVIDER_FAILURE × 2 (HTTP 429). Neither is an observation. Zero statistical impact.

Root cause: the circuit-breaker-open path called `_save_run()` without `checkpoint.record()` (fixed in Amendment 009), and the old watchdog's hardcoded PID check auto-resumed runners that re-executed checkpointed workloads.

---

## Summary table

| Block | Records | LIVE_VALID | Inferential | Status |
|-------|---------|-----------|-------------|--------|
| Original confirmatory (dialagram) | 241 | 234 | **232** | COMPLETE (4/4 cells) |
| Original openrouter free | 238 | 0 | 0 | NON-VIABLE |
| Post-Amendment-010 (openrouter paid) | 49 | 48 | **separate analysis** | IN PROGRESS (cell A: 58/58 COMPLETE, cell C: in progress) |
| **Total** | **528** | **282** | **232 + separate** | |

**Combined "266/464" or "282/464" reporting is PROHIBITED.** Each block reports against its own cell targets independently.
