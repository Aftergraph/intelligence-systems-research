# STUDY-011 Provider Failure Audit

**Generated:** 2026-09-04T08:57:20Z | **Purpose:** integrity monitoring only — NO provider/model/retry changes permitted from these results.

## Distribution (pre-run diagnostic sample, N=87, all NOT_ADMISSIBLE)

| Group | Attempts | LIVE_VALID | PROVIDER_FAILURE | EXCLUDED | Yield | Wilson 95% CI |
|---|---|---|---|---|---|---|
| provider=dialagram | 87 | 44 | 43 | 0 | 0.506 | [0.403, 0.608] |
| model=xiaomi-mimo-2.5 | 29 | 15 | 14 | 0 | 0.517 | [0.344, 0.686] |
| condition=A | 87 | 44 | 43 | 0 | 0.506 | [0.403, 0.608] |
| model=qwen-3.8-max | 28 | 14 | 14 | 0 | 0.5 | [0.326, 0.674] |
| model=deepseek-v4 | 30 | 15 | 15 | 0 | 0.5 | [0.332, 0.668] |

## Assessment

- **Obvious asymmetry:** none observable, but the sample covers only provider=dialagram and condition=A (sequential cell execution had not reached the other cells before the clean stop). Cross-provider and cross-condition symmetry is NOT assessable from this sample.
- **Cell-specific missingness:** cannot be assessed — only 1 of 8 cells observed.
- **Failure concentration:** failures cluster in the warm-up window (rate-limiter/circuit-breaker cold start); model-level yields are statistically indistinguishable (overlapping CIs).
- **Threat to comparability:** UNKNOWN. Flagged as a potential threat; will be re-assessed at n>=50 per cell during the canonical run (integrity monitoring only).
- **Deviation from preregistered assumptions:** the 75% yield assumption under-estimates the observed warm-up failure rate (observed 50.6% in the diagnostic window). The frozen ceiling mechanics (78/cell, 619 global) are the sanctioned response; cells that cannot reach 58 valid within their cap are declared NON-VIABLE per the frozen stopping rule.

## Corrected wording

The earlier claim "uniform failure pattern, no bias detected" is WITHDRAWN as too strong. Corrected: **"No material asymmetry observed in the available pre-run diagnostic sample; the sample is insufficient to detect or exclude bias. Re-assessment is scheduled at n>=50 per cell."**

## Prohibited actions (explicit)

Do NOT change providers, replace models, alter retry rules, resize samples, alter cell targets or thresholds, or drop difficult workloads based on these observations.
