# JAR-EXP-0017 — Preregistration Amendment 01

**Reason:** Freeze candidate, analysis and failure semantics after DEVELOPMENT and before first HELD_OUT outcome  
**Held-out outcomes inspected:** NO  
**Date:** 2026-09-19

## DEVELOPMENT decision

The prespecified Halo mechanism produced positive exploratory worst-context DEVELOPMENT evidence and is carried forward without modification.

No post-DEVELOPMENT tuning is permitted.

## Frozen search

Within every seed, one fixed-operator repertoire is evolved and reused by both selector arms.

```text
seeds: 0..29
population_size: 12
generations: 6
search algorithm: fixed-operator VERGE Repertoire Core
search runs per seed: 1 shared repertoire
```

## Frozen selectors

### Comparator

`NOMINAL`

- target-context feasibility filter;
- nearest source descriptor;
- target-utility tie-break;
- fail closed if no target-feasible elite exists.

### Candidate

`HALO`

- nominal target feasibility filter;
- fixed uncertainty halo;
- require feasibility across all halo points;
- maximize worst halo utility;
- then mean halo utility;
- then descriptor proximity;
- fail closed if no halo-feasible elite exists.

## Frozen uncertainty halo

```text
confidence shocks = [0.00, 0.02, 0.04]
latency shocks    = [0.00, 0.10]
cost shocks       = [0.00, 0.10]
```

Cartesian product: up to 12 deterministic points per target.

Bounded fields are clipped to [0,1].

## Frozen context manifest

`3e6fe4440172a8244d41a01ad1e944bd21fbdc27090230a0b7c8a769622c744d`

HELD_OUT contains four frozen contexts.

## Frozen primary endpoint

For each seed:

```text
WorstHalo(seed) =
  min actual-target utility over HELD_OUT contexts
  after HALO selection

WorstNominal(seed) =
  min actual-target utility over HELD_OUT contexts
  after NOMINAL selection

DeltaWorst(seed) =
  WorstHalo(seed) - WorstNominal(seed)
```

The uncertainty-halo utilities are used for **selection**, not as the primary outcome. Primary outcome utility is always measured at the actual frozen HELD_OUT target context.

## Frozen statistics

```text
30 seed-level DeltaWorst values
10,000 paired bootstrap resamples
random.Random(1717)
95% nearest-rank interval
lower rank 250  -> index 249
upper rank 9750 -> index 9749
```

Positive support requires:

1. observed candidate UAR = 0;
2. observed candidate evidence-integrity failures = 0;
3. mean DeltaWorst > 0;
4. bootstrap CI lower bound > 0;
5. no HELD_OUT context family has systematic candidate safety failure.

## Frozen fail-closed semantics

No eligible selector result remains data.

```text
action = no execution
verified_success = 0
false_completion = 0
unauthorized_actions = 0
evidence_integrity_failures = 0
selection_failure = 1
primary utility = -10000
cost = 0
latency = 0
```

This prevents abstention from receiving artificially favorable utility.

## Secondary reporting

Always report:

- mean actual-target utility;
- VSR/FCR/UAR;
- evidence-integrity failures;
- selection failures;
- recovery successes;
- human interventions;
- cost and CPVO;
- aggregate latency;
- selector evaluation overhead;
- per-context result.

Selector-evaluation overhead is not folded into domain cost unless a separately frozen cost model says so; it is reported independently.

## No-retuning rule

After this amendment, any change to:

- contexts;
- candidate;
- comparator;
- halo perturbations;
- search algorithm;
- population/generations/seeds;
- selector ranking;
- feasibility rules;
- utility;
- primary endpoint;
- failure semantics;
- bootstrap rule

requires a new experiment ID.

## Claim boundary

A positive HELD_OUT result may support only:

> internal deterministic evidence for robust Halo selection on the frozen JAR-EXP-0017 synthetic uncertainty problem class.
