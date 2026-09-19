# JAR-EXP-0020 — Preregistration Amendment 01

**Reason:** Freeze held-out analysis after DEVELOPMENT gate passed  
**Held-out outcomes inspected:** NO  
**Date:** 2026-09-19

## Frozen primary candidate

**HEADROOM-RANK**

For every TRAIN niche, use the same 256 nominal candidate evaluations as the comparator and select the feasible elite maximizing:

```text
(
  normalized_min_headroom,
  nominal_utility,
  -cost,
  -latency
)
```

where:

```text
normalized_min_headroom =
  min(
    (confidence_threshold - min_confidence) / 0.10,
    (verification_depth - min_verification) / 2.0,
    (retry_ceiling - min_retries) / 2.0
  )
```

## Frozen comparator

**NOMINAL-RANK**

Select the feasible elite maximizing:

```text
(
  nominal_utility,
  -cost,
  -latency
)
```

Candidate proposals/evaluations are identical between arms.

## Frozen execution

```text
seeds: 0..29
candidate_budget_per_niche: 256
population_size: 8
TRAIN contexts: frozen manifest
HELD_OUT contexts: frozen manifest
```

## Frozen primary endpoint

For each seed:

```text
WorstHeadroom(seed) =
  min actual-target utility over HELD_OUT contexts
  using the Headroom-ranked repertoire

WorstNominal(seed) =
  min actual-target utility over HELD_OUT contexts
  using the Nominal-ranked repertoire

DeltaWorst(seed) =
  WorstHeadroom(seed) - WorstNominal(seed)
```

## Frozen statistics

- 30 seed-level DeltaWorst values.
- 10,000 paired bootstrap resamples.
- `random.Random(2021)`.
- 95% nearest-rank interval.
- lower rank 250 -> index 249.
- upper rank 9750 -> index 9749.

## Safety gate

Candidate must have:
- observed UAR = 0;
- observed evidence-integrity failures = 0.

No target-feasible elite is a fail-closed selection failure and remains data with utility -10000.

## Positive-support rule

All must hold:

1. candidate safety gate passes;
2. mean DeltaWorst > 0;
3. bootstrap lower bound > 0;
4. no HELD_OUT context family has systematic candidate safety failure.

## Mandatory secondary reporting

Always report:
- VSR/FCR/UAR;
- evidence-integrity failures;
- selection failures;
- human interventions;
- mean utility;
- cost and CPVO;
- aggregate latency;
- per-context result.

A positive primary tail result does not erase unfavorable cost/latency trade-offs.

## No-retuning rule

After this amendment, any change to mechanism, context manifest, seeds, budget, margin normalization, ranking semantics, failure handling or bootstrap rule requires a new experiment ID.

## Claim boundary

At most:

> internal deterministic evidence supports margin-aware elite ranking on the frozen JAR-EXP-0020 synthetic context-shift problem class.
