# JAR-EXP-0015 — VERGE Exploratory S2 Pilot v0.1

**State:** EXPLORATORY — NOT CONFIRMATORY  
**Evidence class:** deterministic synthetic mission simulation  
**Dataset:** `data/verge_pilot_s2_v2.json`  
**Dataset SHA-256:** `3f3bb181b677a92817b1f641d04b85426206eefc376aa5719454de89239dfb61`  
**Benchmark manifest:** `296a859947a0f389e811a9eea110876b6738567de8eba5748ce854cbf604dc7d`

## Design

- 30 paired seeds: 0–29.
- 6 algorithm conditions.
- Population 10.
- 5 evolutionary generations.
- 60 candidate evaluations per condition per seed.
- 180 algorithm/seed runs total.
- Same frozen S2 case manifest across conditions.
- No provider/network calls.
- No production mutations.
- Result is developmental evidence only.

## Results

| Condition | Mean best quality | Mean VSR cases | Mean FCR | Mean UAR | Mean CPVO | Mean latency |
|---|---:|---:|---:|---:|---:|---:|
| B0 Random | -2597.052 | 5.433 | 2.567 | 0.100 | 3.4453 | 14.0055 |
| B1 Fixed governed | 822.326 | 8.000 | 0.000 | 0.000 | 2.8893 | 15.2226 |
| B2 Simple GA | 823.330 | 8.000 | 0.000 | 0.000 | 2.8871 | 11.2486 |
| B5 Pareto-style | **823.388** | 8.000 | 0.000 | 0.000 | 2.8813 | **11.1284** |
| B6 QD-style | 823.357 | 8.000 | 0.000 | 0.000 | **2.8628** | 11.6079 |
| B11 VERGE | 823.082 | 8.000 | 0.000 | 0.000 | 2.8824 | 12.3305 |

## Paired seed result for VERGE quality

| Baseline | Mean VERGE−baseline quality | VERGE wins | Ties | VERGE losses |
|---|---:|---:|---:|---:|
| B0 Random | +3420.134 | 22 | 3 | 5 |
| B1 Fixed | +0.756 | 26 | 4 | 0 |
| B2 Simple GA | -0.248 | 4 | 9 | 17 |
| B5 Pareto-style | -0.306 | 4 | 9 | 17 |
| B6 QD-style | -0.275 | 6 | 9 | 15 |

## Hypothesis verdict at this evidence level

The original H1 is **NOT SUPPORTED by this developmental S2 pilot**.

VERGE clearly exceeds random search and the fixed governed policy on the internal exploratory quality score, while all governed/evolutionary conditions achieve 8/8 verified cases with zero observed false completion and zero observed unauthorized action in their selected best policies.

However, full VERGE does **not** outperform the strongest evolutionary baselines. B5 Pareto-style has higher mean exploratory quality and lower latency; B6 QD-style has lower CPVO. Therefore this pilot cannot support a claim that the combined VERGE mechanism is superior.

This is a useful falsification result, not a failed experiment.

## Root-cause interpretation to test next

The current S2 representation evolves one static policy across all mission cases. The frozen cases have a largely common safe optimum, so the benchmark provides little opportunity for a portfolio/diversity mechanism to demonstrate value.

Additionally:

1. the QD archive in VERGE is currently primarily retention/evidence infrastructure rather than a strong parent-selection driver;
2. adaptive operator selection spends evaluations across four operator classes while simpler baselines exploit a narrow numeric search effectively;
3. the island abstraction exists but is not yet integrated into the main evolutionary loop;
4. routing policies are categorical, while the initial implementation's strongest local improvements are numeric;
5. the internal scalar quality is a developmental search aid, not a preregistered confirmatory primary endpoint.

These observations motivate representation/algorithm work before confirmatory execution. They do **not** authorize changing a confirmatory benchmark after seeing outcomes.

## What is proven versus not proven

### Mechanically demonstrated

- deterministic reproducibility on frozen seeds;
- exact matched evaluation budgets in the pilot;
- evidence-gated verified-success calculation;
- hard rejection of unauthorized/evidence-integrity candidates from the QD archive;
- stable candidate hashing and lineage receipts;
- fail-closed benchmark-manifest hash mismatch;
- final VERGE selection remains feasible across the frozen 30-seed regression pack after the safety fix.

### Not established

- superiority on real agents;
- superiority over NSGA-II or canonical MAP-Elites implementations;
- external validity;
- provider/model robustness;
- generalization to unseen mission families;
- production readiness;
- zero population-level safety risk.

## Next falsification step

Do not promote VERGE.

The next developmental study should separate:

1. **single-policy optimization**, where simple GA/Pareto/QD are strong baselines; and
2. **context-conditional policy portfolio selection**, where diversity has a testable reason to matter.

A held-out mission-family split and exact primary Pareto/statistical rule must be frozen before any confirmatory test.
