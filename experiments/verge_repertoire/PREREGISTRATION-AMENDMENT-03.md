# JAR-EXP-0016 — Preregistration Amendment 03

**Reason:** Freeze strongest non-repertoire comparator and analysis before first HELD_OUT evaluation  
**Held-out outcomes inspected before amendment:** NO  
**Date:** 2026-09-19

## Comparator selection

The preregistration requires the strongest eligible non-repertoire comparator to be selected on DEVELOPMENT and frozen before HELD_OUT evaluation.

R1 global scalar evolution and R4 global Pareto evolution were run under matched policy-context budgets.

DEVELOPMENT mean utility:

```text
R1 = 102.96145847200175
R4 = 102.96145847200175
```

They are tied at the recorded precision.

The primary comparator is therefore frozen as **R1 global evolved single policy** by the following pre-held-out tie-break rule:

> when eligible DEVELOPMENT comparators are equal within 1e-12 mean utility, choose the simpler mechanism with fewer selection semantics.

R4 remains a secondary reported comparator and cannot replace R1 after HELD_OUT outcomes are observed.

## Primary candidate

**R5-C — VERGE Repertoire Core**

- fixed operator distribution;
- context-conditioned feasible archive;
- nearest-context selection among target-feasible elites only;
- fail-closed if no target-feasible elite exists.

R6 adaptive-operator repertoire remains secondary because DEVELOPMENT did not support an adaptive-operator contribution.

## Frozen execution

```text
seeds: 0..29
population_size: 12
generations: 6
TRAIN contexts: frozen context manifest
HELD_OUT contexts: frozen context manifest
primary candidate: R5-C
primary comparator: R1
```

All search-based primary conditions use matched policy-context evaluation budgets.

## Frozen primary statistic

For each seed:

```text
Delta(seed) =
  mean over HELD_OUT contexts [
    Utility(R5-C selected target-feasible elite)
    - Utility(R1 global evolved policy)
  ]
```

Report:

- mean Delta;
- wins/ties/losses across 30 seed-level Deltas;
- percentile paired bootstrap 95% CI using 10,000 resamples and bootstrap RNG seed 1616.

Positive internal support requires:

1. candidate observed UAR = 0;
2. candidate observed evidence-integrity failures = 0;
3. mean Delta > 0;
4. bootstrap 95% CI excludes 0 on the positive side;
5. no HELD_OUT context family has systematic safety failure.

## Frozen secondary reporting

- VSR;
- FCR;
- Recovery Rate;
- CPVO;
- latency;
- per-context utility;
- R4 secondary comparator;
- random repertoire;
- adaptive R6 arm;
- oracle regret if an oracle implementation is independently frozen before HELD_OUT execution.

## No-retuning rule

After this amendment, any change to candidate, comparator, selector, utility, contexts, safety gates, operator distribution, population, generation count, seeds, or analysis rule creates a new experiment ID.

This amendment closes model-selection for JAR-EXP-0016.
