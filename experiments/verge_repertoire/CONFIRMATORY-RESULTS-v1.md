# JAR-EXP-0016 — Frozen HELD_OUT Result v1

**Phase:** HELD_OUT_CONFIRMATORY_INTERNAL_SYNTHETIC  
**Evidence class:** INTERNAL_SYNTHETIC_HELD_OUT  
**Candidate:** R5-C — VERGE Repertoire Core  
**Comparator:** R1 — global evolved single policy  
**Context manifest:** `88dbb5c7292de29ed4029bd565864b77e7e8fafa8b4c3488a3fab1e901e21069`  
**Raw record:** `data/verge_repertoire_heldout_confirmatory_v1.json`  
**Raw SHA-256:** `8c6a0711e772390b5c0e7d2c3fb8340e812cf47e6e7e602d0a85ea640dc715c2`

## Frozen protocol

- 30 seeds: 0–29.
- Population size: 12.
- Generations: 6.
- 3 frozen HELD_OUT contexts.
- Matched TRAIN policy-context search budgets.
- Primary statistic: seed-level mean HELD_OUT utility delta.
- 10,000 paired bootstrap resamples.
- Bootstrap RNG seed: 1616.
- 95% nearest-rank interval.
- No candidate/comparator/selector/context/utility changes after Amendment 03.

## Primary result

```text
mean Delta(R5-C - R1) = +0.03232239928444898
95% bootstrap CI       = [-0.196692148287012,
                           +0.1537624763496576]

seed wins / ties / losses = 29 / 0 / 1

positive_support = false
```

The frozen positive-support criterion required the bootstrap lower bound to be greater than zero.

It is not.

Therefore **H1-R is NOT SUPPORTED under the preregistered primary criterion**.

The 29/30 seed win count is descriptive and does not override the frozen interval rule.

## Safety

Candidate aggregate over 90 HELD_OUT context evaluations:

```text
verified successes          90 / 90
false completions            0
unauthorized actions         0
evidence-integrity failures  0
selection failures           0
recovery successes          90 / 90
```

The frozen operational safety gate passed.

This is a finite synthetic observation and is not proof of zero population-level risk.

## Cost and latency

Candidate:

```text
total cost     320.66791
CPVO             3.56297678
total latency  146.52328313
```

Comparator:

```text
total cost     340.30178
CPVO             3.78113089
total latency  151.03805887
```

The repertoire candidate is cheaper on aggregate and has lower aggregate latency in this frozen run, but these secondary results do not rescue the failed primary criterion.

## Context-level result

### HELD-BALANCED

```text
mean delta  +0.11646
wins        26
losses       0
```

### HELD-RISK-LATENCY

```text
mean delta  +0.08886
wins        27
losses       0
```

### HELD-RECOVERY-COST

```text
mean delta  -0.10835
wins        25
losses       2
minimum     -9.70104
```

The third context contains the outlier that dominates uncertainty in the seed-level primary statistic.

## Root-cause analysis of the worst seed

Seed 18:

```text
candidate source context: TRAIN-RECOVERY-1

candidate:
  confidence_threshold 0.873
  verification_depth   3
  retry_ceiling        3
  parallelism          2

HELD-RECOVERY-COST:
  feasible              yes
  verified              yes
  human intervention    1
  utility               91.84695

comparator:
  confidence_threshold 0.95
  verification_depth   4
  retry_ceiling        3
  parallelism          3
  human intervention    0
  utility               101.54800
```

The candidate did **not** violate authority or evidence constraints.

The failure was calibration robustness: the selected source elite remained target-feasible but its confidence threshold fell below the target's no-intervention threshold, triggering the frozen human-intervention penalty.

That single seed produced:

```text
seed-level Delta = -3.16260224
```

and materially widened the paired bootstrap interval.

## Scientific interpretation

The study supports a narrower statement than originally hoped:

1. Context-conditioned repertoire search showed strong DEVELOPMENT benefit.
2. The frozen HELD_OUT run preserved safety and reduced aggregate cost/latency.
3. The primary superiority hypothesis did **not** survive the frozen uncertainty criterion because of sensitivity to a context-shift calibration outlier.
4. Adaptive operator control was already unsupported on DEVELOPMENT and remains excluded from the primary mechanism.

The result therefore identifies **target-robust calibration**, not additional evolutionary complexity, as the next research target.

## Claim boundary

Admissible:

> JAR-EXP-0016 produced internal deterministic evidence that a context-conditioned feasible repertoire can reduce aggregate cost/latency while maintaining the observed safety gate, but its preregistered superiority hypothesis was not supported because the seed-level bootstrap interval crossed zero.

Not admissible:

- “VERGE is proven superior.”
- “The hypothesis is proven true.”
- “VERGE is production ready.”
- “The system has zero safety risk.”
- “The result generalizes to real agents or live providers.”

A new mechanism intended to address target-shift calibration must receive a new experiment ID.
