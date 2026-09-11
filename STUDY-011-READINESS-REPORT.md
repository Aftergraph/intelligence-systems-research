# STUDY-011 Readiness Report v4.0 — Confirmatory Execution Complete

**Version:** 4.0  
**Date:** 2026-09-11  
**Status:** `FINAL_FROZEN` — confirmatory execution and analysis complete  
**Program maturity:** Level C+ / Provisional-D; blind external reproduction remains pending  
**Supersedes:** v3.0 `RUNNING`, v2.0 `READY_FOR_OWNER_APPROVAL`

---

## 0. Canonical Status

STUDY-011 is no longer a readiness-only or running study.

The preregistered cross-provider confirmatory run has been executed, reconciled and frozen under the post-execution protocol amendments. The canonical evidence cut is:

- dataset: `data/study011_runs/confirmatory/canonical-run-002/`
- analysis: `data/study011_runs/confirmatory/canonical-run-002-analysis/`
- final summary: `data/study011_runs/confirmatory/canonical-run-002-analysis/FINAL-CONFIRMATORY-SUMMARY.md`
- post-execution freeze: `STUDY-011-AMENDMENT-011-POST-EXECUTION-FREEZE.md`
- valid sample: **470 `LIVE_VALID` records**
- coverage: **8/8 cells with at least 58 observations**

This report describes readiness/execution state only. The frozen analysis artifacts remain authoritative for statistical detail.

---

## 1. Frozen Confirmatory Verdicts

| Hypothesis | Final verdict | Frozen interpretation |
|---|---|---|
| **H1 — assurance lowers FCR** | **REVERSED** | A/C models frequently abstained, causing baseline FCR to floor at/near zero; G could not improve a zero floor |
| **H2 — authority+budget adds effect over F** | **SUPPORTED** | Both provider strata satisfy the preregistered direction with `p < 0.001` and effect size `h ≈ 2.5` |
| **H3 — retry alone adds effect** | **REVERSED** | C abstained similarly to A; retry without assurance did not produce the predicted effect |

The correct mechanistic reading is deliberately narrow: Condition F (assurance invocation) produces the main abstention→action transition; Condition G adds the separately measured authority+budget effect over F. Do not rewrite this as a blanket claim that the full governance stack universally “unlocks” models.

---

## 2. Integrity / Freeze State

| Gate | Current state |
|---|---|
| Pre-registration | Frozen before confirmatory look, with amendments preserved |
| `LIVE_ONLY` execution boundary | Enforced for confirmatory evidence |
| Canonical data reconciliation | Complete; Amendment-010 lineage/fingerprint preference governs duplicates |
| Canonical sample | 470 `LIVE_VALID`; 8/8 cells ≥58 |
| Final analysis | Complete and frozen |
| H1 | `REVERSED` |
| H2 | `SUPPORTED` |
| H3 | `REVERSED` |
| Post-execution freeze | Amendment 011 |
| Statistical-review disposition | `SOUND_WITH_HEDGES_REQUIRED` |
| Human-subject validation | Still open; `N=0` live humans |
| Blind external reproduction | Still open |

The raw records contain 243 duplicate `run_id` lines from checkpoint/resume rewrites. The frozen analysis resolves them according to G7 semantics and Amendment-010 lineage preference. This is documented evidence handling, not silent row deletion.

---

## 3. What Changed From v3.0

v3.0 correctly recorded that the pre-confirmatory engineering/research blockers were green and that execution had begun, but its `RUNNING` status became stale once the canonical run and final analysis were frozen.

The following v3/v2 statements are therefore **historical only** and must not be surfaced as current state:

- `RUNNING`;
- `READY_FOR_OWNER_APPROVAL`;
- `Live confirmatory matrix: NOT YET EXECUTED`;
- `awaiting owner approval` as the next action.

Historical versions remain recoverable through Git history. They are intentionally not duplicated verbatim here because embedding obsolete current-state tables inside the active report caused automated and human consumers to recover conflicting statuses.

---

## 4. Remaining Research Gates

Completion of STUDY-011 does **not** imply overall program completion or external validation. The following remain separate gates:

1. reconcile claim/hypothesis registries and publications to the frozen result;
2. preserve H1/H3 reversals as valid preregistered outcomes;
3. run live human-subject work before human-efficiency/preference claims;
4. obtain blind independent external reproduction before external-replication maturity claims;
5. continue STEAD/prior-art overlap analysis and narrow novelty where external formal work already covers the same property;
6. keep simulation, live-pilot, live-confirmatory, human, formal and external-replication evidence classes distinct.

---

## Document Control

| Field | Value |
|---|---|
| Version | 4.0 |
| Status | `FINAL_FROZEN` |
| Current as of | 2026-09-11 |
| Canonical result | H1 `REVERSED`; H2 `SUPPORTED`; H3 `REVERSED` |
| Canonical sample | 470 `LIVE_VALID`, 8/8 cells ≥58 |
| Supersedes | v3.0 (`RUNNING`) and v2.0 (`READY_FOR_OWNER_APPROVAL`) |
| Next action | Reconcile current-facing claims/publications; do not re-run or reinterpret frozen confirmatory evidence without a new preregistered study |
