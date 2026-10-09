# JAR-EXP-0015 Preregistration — VERGE

**Title:** Verified Evolutionary Routing with Governed Exploration  
**Status:** PREREGISTRATION DRAFT — NOT YET EXECUTED  
**Date:** 2026-09-19  
**Canonical owner:** Aftergraph/intelligence-systems-research

## 1. Research question

Does VERGE improve verified agent-execution outcomes over fixed governed policies and conventional evolutionary baselines under equal evaluation budgets, without increasing unauthorized-action rate?

## 2. Hypotheses

### Primary

**H0:** No reproducible improvement in the preregistered verified-outcome comparison against the strongest eligible baseline.

**H1:** Full VERGE improves the preregistered verified-outcome comparison against the strongest eligible baseline while maintaining the frozen safety constraint.

### Secondary

**H2:** Quality-Diversity archive retention improves out-of-distribution robustness to failure-mode/task-family shift versus the no-QD ablation.

**H3:** Adaptive operator selection improves evaluation efficiency versus fixed operator probabilities.

**H4:** Semantic LLM mutation improves cost-normalized search efficiency versus non-LLM mutation; otherwise it is rejected from the default system.

## 3. Independent variable

Algorithm condition:

- B0 Random search
- B1 Fixed governed policy
- B2 Simple GA
- B3 Differential Evolution numeric subspace
- B4 CMA-ES numeric subspace
- B5 NSGA-II
- B6 MAP-Elites
- B7 LLM-only iterative rewrite
- B8 VERGE - adaptive operator selection
- B9 VERGE - QD archive
- B10 VERGE - LLM mutation
- B11 Full VERGE

## 4. Dependent variables

Primary:

- VSR — Verified Success Rate
- FCR — False Completion Rate
- UAR — Unauthorized Action Rate
- CPVO — Cost Per Verified Outcome
- TVO — Time to Verified Outcome
- HIR — Human Intervention Rate
- RR — Recovery Rate

Search diagnostics:

- hypervolume
- QD archive coverage
- QD score
- generation-to-improvement
- operator entropy
- stagnation duration
- token/context use
- tool-call count

## 5. Safety constraint

Confirmatory success requires:

```text
UAR = 0
```

for the frozen authority-critical evaluation set.

Any evidence fabrication or verifier-bypass event is a feasibility failure and is separately reported.

## 6. Evaluation strata

### S1 — optimization mechanics

Deterministic continuous functions: Sphere, Rosenbrock, Rastrigin, Ackley.

Purpose: implementation sanity and optimizer behavior only.

No agent-system claim may be derived from S1.

### S2 — controlled mission simulation

Frozen mission cases covering:

- stale state
- tool timeout
- malformed tool output
- dependency blocker
- context loss
- authority revocation
- verifier failure
- parallel write collision
- false-completion temptation
- provider/tool unavailability

### S3 — controlled real-agent missions

S3 is protected and cannot begin from this preregistration alone.

S3 requires a separate explicit run authorization, exact environment/model/tool pins, cost ceilings, and a clean preflight receipt.

## 7. Randomization and seeds

- S1/S2 conditions use the same frozen task set.
- Algorithms receive matched evaluation budgets.
- Each deterministic benchmark cell uses at least 30 independent seeds unless a pre-execution power analysis freezes a larger requirement.
- Seeds are generated and frozen before outcome inspection.
- Candidate initialization order is randomized per seed and recorded.

## 8. Selection and evaluation budget

The unit of budget is a candidate evaluation against one benchmark case.

Comparison claims must use equal evaluation budgets. Wall-clock and monetary cost are reported separately and may not be hidden by equal-evaluation accounting.

If an algorithm cannot consume the same representation, the comparison is explicitly restricted to the common subspace.

## 9. Primary decision rule

The confirmatory primary comparison is:

```text
Full VERGE (B11)
vs
strongest eligible non-VERGE baseline among B1-B7
```

The strongest baseline is selected by the preregistered multi-objective comparison on the development split, then frozen before confirmatory evaluation.

A positive VERGE verdict requires all of:

1. no safety-constraint failure;
2. improvement on the frozen primary verified-outcome comparison;
3. confidence interval/effect-size evidence meeting the frozen analysis threshold;
4. gain survives cost normalization;
5. no material collapse on held-out task families.

## 10. Statistical plan

Before execution, the analysis script and thresholds are frozen.

Default analysis:

- paired comparisons on matched task/seed blocks;
- bootstrap confidence intervals for principal rate/cost differences;
- Wilson intervals for binary rates where appropriate;
- nonparametric paired tests if distributional assumptions are not defensible;
- Holm correction across confirmatory pairwise comparisons;
- standardized and domain-appropriate effect sizes;
- Pareto hypervolume with a preregistered reference point;
- held-out robustness reported separately from in-distribution optimization.

Exact tests and thresholds must be encoded in the frozen analysis manifest before any confirmatory result is inspected.

## 11. Ablations

Ablations B8-B10 are mandatory.

Mechanism-support claims require the relevant full-vs-ablation comparison.

If full VERGE wins but no mechanism ablation shows measurable contribution, the empirical result may support the system configuration but not the claimed mechanism explanation.

## 12. Exclusion criteria

A run may be excluded only for preregistered infrastructure invalidity such as:

- harness crash before candidate execution;
- corrupted receipt;
- benchmark/version hash mismatch;
- evaluator unavailable before producing a verdict;
- environment contamination outside the frozen tolerance.

Algorithm failures, timeouts, invalid candidates, and poor outcomes remain data.

All exclusions are retained in raw records with explicit reason codes.

## 13. Stopping rule

No early stop for favorable outcomes.

A cell stops when the frozen evaluation budget is exhausted or a safety stop invalidates further execution under the protocol.

Safety stops remain results; they do not silently disappear.

## 14. Falsification criteria

H1 is refuted or remains unsupported if any of the following occurs:

- B11 fails the frozen safety constraint;
- B11 does not outperform the strongest eligible baseline under the primary decision rule;
- apparent benefit disappears after equal-budget/cost normalization;
- benefit fails on the held-out task-family evaluation;
- result is dominated by one or a few seeds;
- a materially simpler policy matches the frontier.

H2/H3/H4 are independently falsifiable and do not inherit H1.

## 15. Reproducibility record

Every confirmatory record must bind:

- repository exact SHA
- algorithm version/hash
- benchmark version/hash
- candidate lineage
- seed
- model/provider/tool versions if used
- environment/hardware
- timestamps
- raw evaluator outputs
- evidence references
- cost and latency
- exclusion/validity state

Target reproduction interface:

```text
python -m experiments.verge reproduce --manifest <frozen-manifest>
```

This command is a target interface only until implementation lands.

## 16. Evidence boundary

No result exists yet.

This preregistration does not establish that VERGE works, is novel, is production-ready, or improves Aftergraph.

Claims advance only after execution, analysis, hostile review, and evidence registration.
