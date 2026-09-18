# STUDY-012 Full Matrix Post-Run Report — 2026-09-18

**Execution status:** COMPLETED (960 unique traces)  
**Confirmatory inference status:** BLOCKED — provider availability confound  
**Raw observations SHA-256:** `9e712249555180fcc32fb22c0a0b99298d09e7dda114f92b97d2e6de3ce08411`

## Execution accounting

- Planned observations: 960
- Written observations: 960
- Unique trace IDs: 960
- Runner API-call counter: 1910
- Recorded estimated/provider cost: USD 0.01801667
- Hard cost cap: USD 4.00
- Harness failures: 0
- LIVE_VALID task responses: 222 (23.125%)
- LIVE_PROVIDER_FAILURE: 738 (76.875%)

Provider split:
- Google Direct: 7/480 LIVE_VALID; 473/480 provider failures.
- OpenRouter: 215/480 LIVE_VALID; 265/480 provider failures.

Three R2 classes had zero LIVE_VALID task observations:
`adversarial_evidence`, `crash_recovery`, `replay`.

Therefore the preregistered 8-class confirmatory claims are **not admissible** from this run. Missing cells are not treated as null results and are not imputed.

## Admissible subset diagnostics

- J: 53 observations had both a live task response and live judge response.
  - judge ABSTAIN: 48
  - judge VERIFIED: 5
- JD: 48 observations had both live judge and deterministic evaluation.
  - judge ABSTAIN / deterministic VERIFIED: 40
  - judge VERIFIED / deterministic VERIFIED: 8
  - observed judge/deterministic disagreement count: 40/48
- D: 52 LIVE_VALID task observations; 52 deterministic VERIFIED.
- DI: 47 LIVE_VALID task observations; 47 deterministic + Sentinel VERIFIED; 47 independent `dvr_` receipts present.

These are descriptive diagnostics only. They do not rescue the preregistered confirmatory matrix because provider failures are severe and non-uniform.

## Evidence limitations discovered

1. Provider adapters did not persist sanitized failure reason/status into each failed observation. Root causes of the 738 failures therefore cannot be reconstructed from the frozen rows alone.
2. Judge rows retain verdict + response hash but not judge response text, so ABSTAIN root cause cannot be reconstructed exactly.
3. Provider catalog readiness is not equivalent to inference-path readiness.
4. The earlier S12-INC-001 pre-execution harness incident remains excluded and MUST NOT be pooled.

## Scientific disposition

This run is retained as a completed empirical execution with a **provider-availability confound**. It may support falsification of the execution harness and descriptive analysis of the admissible subset, but it does not satisfy the frozen confirmatory coverage requirement.

No automatic rerun is authorized by this report.
