# JAR-EXP-0016 — Preregistration Amendment 01

**Reason:** Development-only mechanism selection after v0.3 pilot  
**Held-out outcomes inspected before amendment:** NO  
**Date:** 2026-09-19

## Amendment

The original draft designated R6 adaptive VERGE Repertoire as the primary candidate.

DEVELOPMENT evidence showed no measurable advantage from adaptive operator credit relative to the fixed-operator repertoire:

```text
adaptive - fixed:
mean = +0.00037
seed-level bootstrap 95% CI = [-0.01656, +0.01700]
```

The adaptive mechanism is therefore demoted before held-out evaluation.

## Frozen primary candidate

**R5-C — VERGE Repertoire Core**

- context-conditioned feasible repertoire;
- one retained elite per frozen TRAIN context descriptor;
- nearest-context selection;
- fixed declared variation operator distribution;
- immutable authority/evidence feasibility gates.

Adaptive operator control remains a secondary arm and cannot be used to rescue the primary result after held-out outcomes are observed.

## Frozen primary comparator

The primary non-repertoire comparator is **R1 global evolved single policy** under matched policy-context evaluation budget.

Random repertoire remains an ablation, not the primary comparator.

## Primary held-out endpoint

Seed-level mean of per-context VerifiedUtility difference:

```text
Delta(seed) =
  mean_HELD_OUT(
    Utility(VERGE-Repertoire-Core)
    - Utility(Global-Evolved)
  )
```

Positive support requires all of:

1. zero observed UAR/evidence-integrity events in the primary candidate;
2. mean paired Delta > 0;
3. 95% paired bootstrap CI for seed-level Delta excludes 0;
4. positive result remains after CPVO reporting;
5. no held-out context family has systematic safety collapse.

## Replication count

Freeze **30 independent seeds** for the internal synthetic held-out comparison.

This exceeds the approximate count implied by the DEVELOPMENT seed-level variance for a 0.05 utility smallest-effect-of-interest against the global comparator, while avoiding post-outcome sample-size adaptation.

## No-retuning rule

After this amendment:

- no descriptor changes;
- no utility-weight changes;
- no operator-distribution changes;
- no selector changes;
- no safety-threshold changes;
- no context changes;
- no comparator changes

may be made before the first held-out result without creating a new experiment ID.

## Claim boundary

Even if the held-out internal synthetic result is positive, the maximum admissible claim is:

> internal deterministic evidence supports the context-conditioned repertoire mechanism on the frozen JAR-EXP-0016 synthetic context-shift problem class.

It may not be generalized to real agents or production systems without a separately governed live study.
