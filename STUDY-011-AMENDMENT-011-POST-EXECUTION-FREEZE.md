# STUDY-011 AMENDMENT 011 — Post-Execution Artifact Freeze (Closure)

**Date:** 2026-09-04 17:23 UTC
**Status:** PREREGISTERED — binds dataset immutability (roadmap item 0.1/0.6)

## What changed post-execution (declared, not silent)

1. `experiments/live_benchmark/study011_analyze.py` — summary-writer KeyError('chi2') fix
   for EMPTY/NO_OBSERVATIONS strata (writer only; analysis logic untouched). Post-fix hash: `385984c2fb4e2e44...`
2. Analysis-view derivation (documented in FINAL-CONFIRMATORY-SUMMARY.md): one observation
   per run_id, Amendment-010 lineage preference (dfe3513c), is_live=True only for the
   analysis input. Raw `run_records.jsonl` untouched.

## Dataset freeze

- Canonical dataset: `data/study011_runs/confirmatory/canonical-run-002/` (470 LIVE_VALID, 8/8 cells)
- Canonical analysis: `data/study011_runs/confirmatory/canonical-run-002-analysis/`
- Verdicts: H1 REVERSED / H2 SUPPORTED (p<0.001, h≈2.5, both strata) / H3 REVERSED
- **From this amendment: no mutation of the completed dataset.** Corrections happen only
  via new amendment docs; analysis re-runs may only regenerate derived artifacts from
  the frozen input view.

## Known-failing tests (expected, documented)

- `test_study011_preconfirmatory_freeze.py::test_no_drift_since_gate` — pins the
  PRE-confirmatory gate state; artifact hashes changed via this declared amendment.
  To be re-pinned to post-closure hashes in the closure commit.
- `test_fake_provider_live_only.py::test_runner_cell_math_matches_frozen_plan` — expects
  pre-Amendment-010 ceiling 619; run_math now 931. To be updated to the Amendment-010
  ceiling in the same commit.
