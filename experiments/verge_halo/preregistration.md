# JAR-EXP-0017 Preregistration — VERGE Halo

**Status:** DRAFT — NO HELD_OUT OUTCOMES  
**Date:** 2026-09-19

## Primary candidate

VERGE Halo selector applied to the fixed-operator VERGE Repertoire Core archive.

## Primary comparator

Nominal target-feasible nearest-context selector applied to the **same archive**.

No independent evolutionary search is performed between selector arms.

## Frozen search

- 30 seeds: 0..29.
- population size: 12.
- generations: 6.
- fixed-operator repertoire evolution.
- same repertoire instance reused by candidate and comparator within each seed.

## Frozen halo

```text
confidence shocks = [0.00, 0.02, 0.04]
latency shocks    = [0.00, 0.10]
cost shocks       = [0.00, 0.10]
```

Halo feasibility is conjunctive: an elite must be feasible at every halo point.

## Primary statistic

For each seed:

```text
candidate_worst = min(utility across HELD_OUT contexts using Halo)
baseline_worst  = min(utility across HELD_OUT contexts using Nominal)

DeltaWorst = candidate_worst - baseline_worst
```

Primary report:

- mean DeltaWorst;
- wins/ties/losses;
- 10,000 paired bootstrap resamples;
- RNG seed 1717;
- 95% nearest-rank interval using ranks 250 and 9750.

## Safety gate

Candidate must have:

```text
observed unauthorized actions = 0
observed evidence-integrity failures = 0
```

No target-robust elite is a fail-closed selection failure and remains data.

## Positive-support rule

All must hold:

1. safety gate passes;
2. mean DeltaWorst > 0;
3. bootstrap 95% lower bound > 0;
4. no held-out context family has systematic safety failure.

## Secondary interpretation

Mean utility and CPVO must be reported even if the primary tail metric succeeds.

A positive primary result with severe mean/cost degradation is not enough for a deployment recommendation.

## Claim boundary

Maximum possible claim:

> internal deterministic evidence supports robust neighborhood-aware repertoire selection on the frozen JAR-EXP-0017 synthetic uncertainty problem class.

No real-agent, external-reproduction, or production claim is authorized.
