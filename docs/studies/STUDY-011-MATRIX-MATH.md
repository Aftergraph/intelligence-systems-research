# STUDY-011 Matrix Mathematics

**Status:** FROZEN (matches `data/study011_run_math.json` derivation; executable cross-check: `data/study011_runs/MATRIX-MATH-EXECUTABLE-VERIFICATION.json` — ALL MATCH)

## Definitions (per preregistration)

- **Workload:** one frozen task in `data/study011_workloads_frozen.json` (20 total, root_hash `e823102a…`).
- **Replicate:** one repetition of a workload (3 per workload, seeded via `data/study011_replicate_seed_table.json`).
- **Condition:** treatment arm (confirmatory conditions: A, C, F, G).
- **Model:** exact provider model id from the stratum's frozen model set (dialagram: deepseek-v4, xiaomi-mimo-2.5, qwen-3.8-max; openrouter: gemma-4-31b-it:free, glm-5.2:free). Models rotate round-robin per (workload, replicate) — deterministic from the seed table. Model is part of the analysis pairing key, NOT a cell dimension.
- **Attempt:** one API request + record (any execution class).
- **Observation:** a persisted record in `run_records.jsonl`.
- **LIVE_VALID observation:** an observation classified LIVE_VALID under the frozen classification logic (no simulation fallback; LIVE_ONLY invariant enforced).
- **Inferential cell:** (provider_stratum, condition) — 2 strata x 4 conditions = 8 cells. Models/workloads/replicates pool WITHIN a cell; the analysis unit is (stratum, model, workload, replicate).

## Reconciliation of 1200 vs 464 vs 619

- Execution space: 20 workloads x 3 replicates = 60 nominal attempts per (stratum, condition) cell; 8 cells => 480 nominal attempts (this is `480`, and `1200` counted workloads across ALL conditions x models which double-counts the rotation — the 1200 figure is refuted; see run_math `890_refuted` note for the analogous chat-report error).
- Cell floor: 58 LIVE_VALID per cell (power analysis: two-sided alpha=0.05/4 Bonferroni, power=0.80, h=0.5).
- Total confirmatory target: 8 x 58 = **464** LIVE_VALID.
- Attempt ceiling per cell: ceil(58/0.75) = **78** (75% valid-yield assumption from STUDY-008's 3.3% failure rate x3 buffer).
- Global ceiling: ceil(464/0.75) = **619** attempts total.

## Stopping rules (frozen)

- Per cell: stop when LIVE_VALID >= 58; never exceed 78 attempts.
- Global: stop when all 8 cells viable OR total attempts reach 619.
- If a cell hits its 78-attempt cap below 58 LIVE_VALID: declare the cell NON-VIABLE, document per-stratum stopping reason, NO simulation fallback, NO threshold change.
- Crash-resume: by run_id from checkpoint journal; no double-counting (Amendment 007: checkpoint-before-save ordering).

## Executable verification

`data/study011_runs/MATRIX-MATH-EXECUTABLE-VERIFICATION.json` reconstructs cells, membership, seed allocation and all arithmetic from the frozen artifacts (provider_model_matrix + workload_manifest + replicate_seed_table + run_math). Result: **ALL MATCH** (8 checks pass).
