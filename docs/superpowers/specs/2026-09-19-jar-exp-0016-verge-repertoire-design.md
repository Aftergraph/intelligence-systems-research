# JAR-EXP-0016 — VERGE Repertoire

**Title:** Context-Conditioned Quality-Diversity Evolution for Verified Agent Execution  
**Status:** DESIGN / PREREGISTRATION DRAFT  
**Parent evidence:** JAR-EXP-0015 exploratory S2 falsification result  
**Canonical owner:** Aftergraph/intelligence-systems-research

## Motivation

JAR-EXP-0015 showed that a single static policy search problem did not provide a reason for VERGE's diversity machinery to outperform simpler evolutionary baselines. The strongest simple Pareto/QD baselines matched or exceeded full VERGE on the synthetic S2 objective.

The next falsifiable question is therefore narrower:

> Does maintaining a diverse repertoire of verified policies help when mission context changes and different contexts favor different safe policies?

This is not a continuation of the original superiority claim. It is a new problem-class-specific hypothesis.

## Hypotheses

**H0-R:** A context-conditioned repertoire provides no reproducible benefit over a single-policy optimizer or simple portfolio baselines under held-out context shifts.

**H1-R:** Under matched evaluation budgets, a context-conditioned feasible policy repertoire improves held-out verified-outcome performance after context shift without increasing observed unauthorized actions.

**H2-R:** Repertoire diversity improves recovery after abrupt environment/constraint shifts relative to a Pareto-only single-policy archive.

**H3-R:** Contextual selection from the repertoire improves cost-normalized verified outcomes relative to using the globally best static policy everywhere.

## Scientific basis

The study is motivated by established Quality-Diversity work, where archives preserve high-performing solutions across behavior niches, and by dynamic constrained multi-objective optimization, where objectives/constraints change over time. Prior MAP-Elites work has shown that diversity can improve adaptation when environments change; modern constrained-MOEA reviews identify dynamic constraints as a distinct challenge class.

These sources motivate the hypothesis only. They do not establish that VERGE Repertoire works.

## Problem class

A mission context is defined by a frozen vector:

```text
MissionContext
  risk_class
  failure_pressure
  latency_pressure
  cost_pressure
  verification_demand
  intervention_penalty
```

Each context changes the relative performance of the same policy genome while preserving hard authority/evidence constraints.

The search target is not one policy. It is:

```text
context descriptor
→ feasible elite policy
```

The selector may choose only among policies in the verified feasible repertoire.

## Repertoire descriptors

v0.1 uses three bounded dimensions:

1. risk class;
2. failure/recovery pressure;
3. latency/cost pressure.

The descriptor set is intentionally small to avoid sparse-archive artifacts identified in JAR-EXP-0015 hostile review.

## Hard constraints

- UAR/evidence-integrity violation => infeasible;
- selection cannot choose an infeasible elite;
- authority remains external to the genome;
- context labels cannot modify verifier semantics;
- held-out context definitions are frozen before evaluation;
- no benchmark mutation after outcome inspection.

## Baselines

- R0 global fixed governed policy;
- R1 globally best evolved single policy;
- R2 random feasible repertoire selection;
- R3 nearest-context repertoire without evolution;
- R4 Pareto-only single-policy evolution;
- R5 MAP-Elites-style repertoire;
- R6 VERGE Repertoire.

## Primary outcomes

- held-out Verified Success Rate;
- post-shift Recovery Rate;
- False Completion Rate;
- Unauthorized Action Rate;
- Cost Per Verified Outcome;
- Time/latency to verified outcome;
- regret versus per-context oracle elite.

Safety remains a hard feasibility gate, not a weighted objective.

## Frozen evaluation split

Three partitions:

- TRAIN: contexts available to evolution;
- DEVELOPMENT: contexts available for mechanism debugging/tuning;
- HELD_OUT: unseen context combinations reserved for the final preregistered comparison.

The first executable milestone may inspect TRAIN/DEVELOPMENT only. HELD_OUT outcomes must not be used to tune the mechanism.

## Decision boundary

JAR-EXP-0016 can support H1-R only if:

1. R6 maintains the frozen safety gate;
2. R6 improves the preregistered held-out primary comparison versus the strongest eligible baseline;
3. effect survives cost normalization;
4. gains are not confined to one context family;
5. repertoire ablation demonstrates a measurable contribution beyond extra evaluations.

Otherwise H1-R is unsupported or refuted.

## Evidence boundary

This document creates no positive result. JAR-EXP-0016 starts with zero empirical evidence.
