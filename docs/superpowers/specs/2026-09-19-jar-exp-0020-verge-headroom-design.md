# JAR-EXP-0020 — VERGE Headroom

**Title:** Margin-Aware Elite Ranking Under Context Shift  
**Status:** DESIGN / PREREGISTRATION DRAFT  
**Parent evidence:** JAR-EXP-0019 DEVELOPMENT result

## Trigger

JAR-EXP-0019 removed most of the evaluation-efficiency penalty from robust search, but the frozen DEVELOPMENT interval still crossed zero.

Across JAR-EXP-0018 and JAR-EXP-0019, TRAIN robust-feasibility coverage was already saturated at 1.0 for both candidate and nominal arms.

The next problem is therefore not finding feasible policies. It is ranking among feasible policies with different robustness margins.

## Hypothesis

**H0-H:** Margin-aware elite ranking provides no reproducible benefit over nominal utility ranking under matched search and evaluation budgets.

**H1-H:** Ranking feasible elites using frozen safety/recovery headroom improves held-out worst-context verified utility without increasing observed UAR, evidence-integrity failures, or selection failures.

## Headroom vector

For a feasible policy-context pair:

```text
confidence_headroom =
  confidence_threshold - min_confidence

verification_headroom =
  verification_depth - min_verification

retry_headroom =
  retry_ceiling - min_retries
```

Only nonnegative feasible headroom is eligible.

## Candidate ranking

Candidate and comparator receive the same nominal candidate evaluations.

Comparator ranks by nominal utility.

Headroom ranks lexicographically by:

1. feasible;
2. minimum normalized headroom;
3. nominal utility;
4. lower cost;
5. lower latency.

No additional halo evaluation is required.

## Scientific objective

Test whether robustness margin can recover target-shift calibration at essentially zero extra evaluation cost.

New context manifest and new held-out outcomes are required.
