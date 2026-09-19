# JAR-EXP-0018 Preregistration — VERGE Bastion

**Status:** DRAFT — NO HELD_OUT OUTCOMES  
**Date:** 2026-09-19

## Primary candidate

**Bastion robust repertoire evolution**

- fixed operator distribution;
- source-niche search;
- robustness evaluated during TRAIN;
- robust-feasible candidate must remain feasible across every frozen training-halo point;
- source elite ranking uses worst halo utility, then mean halo utility.

## Primary comparator

**Nominal fixed-operator repertoire evolution**

- same genome representation;
- same variation operators;
- same TRAIN niches;
- nominal-only candidate evaluation.

## Fair budget

Total policy-context evaluation count is frozen equal across primary arms.

Robust candidate evaluations consume multiple halo points and therefore fewer candidate proposals under the same total budget.

## Search configuration

- 30 seeds: 0..29.
- TRAIN / DEVELOPMENT / HELD_OUT manifest frozen before any HELD_OUT run.
- fixed operators only.
- no adaptive operator credit.
- nominal nearest target-feasible selector for both primary arms.

## Training halo

```text
confidence shocks = [0.00, 0.02]
latency shocks    = [0.00, 0.08]
cost shocks       = [0.00, 0.08]
```

## Primary statistic

For each seed:

```text
DeltaWorst =
  min HELD_OUT actual-target utility(Bastion)
  -
  min HELD_OUT actual-target utility(Nominal)
```

Report:
- mean DeltaWorst;
- wins/ties/losses;
- 10,000 paired bootstrap resamples;
- RNG seed 1818;
- 95% nearest-rank interval, ranks 250 and 9750.

## Safety gate

Candidate must have:
- observed UAR = 0;
- observed evidence-integrity failures = 0.

Fail-closed selector outcomes remain data and receive primary utility -10000.

## Positive support

All must hold:
1. safety gate passes;
2. mean DeltaWorst > 0;
3. bootstrap lower bound > 0;
4. no held-out context family has systematic candidate safety failure.

## Secondary guardrails

A positive tail result must be accompanied by:
- VSR;
- mean utility;
- selection failures;
- CPVO;
- latency;
- intervention count;
- total search evaluation cost.

## Claim boundary

Maximum possible claim:

> internal deterministic evidence supports robust search-time repertoire evolution on the frozen JAR-EXP-0018 synthetic uncertainty problem class.

No external, live-agent or production claim is authorized.
