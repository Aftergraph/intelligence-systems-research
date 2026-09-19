# JAR-EXP-0018 — VERGE Bastion

**Title:** Robust Repertoire Evolution Under Context Uncertainty  
**Status:** DESIGN / PREREGISTRATION DRAFT  
**Parent evidence:** JAR-EXP-0017 frozen HELD_OUT result  
**Canonical owner:** Aftergraph/intelligence-systems-research

## Trigger

JAR-EXP-0017 falsified the hypothesis that robust post-hoc selection alone is sufficient.

The failure localized to a high-risk held-out region where the nominally evolved repertoire did not contain any elite that remained feasible across the frozen uncertainty halo.

This motivates a different mechanism:

> robustness must influence search pressure while the repertoire is being evolved.

## Hypotheses

**H0-B:** Robust halo-aware evolution provides no reproducible improvement in held-out worst-context verified utility versus nominal repertoire evolution when both use the same search budget.

**H1-B:** Under matched total policy-context evaluation budgets, halo-aware repertoire evolution improves seed-level worst-context verified utility on unseen context shifts without increasing observed unauthorized actions or evidence-integrity failures.

**H2-B:** Robust search improves robust archive coverage rather than merely replacing execution with fail-closed abstention.

**H3-B:** Any tail-risk gain remains acceptable on mean utility, CPVO, latency and verified completion coverage.

## Mechanism

### Nominal repertoire evolution

Each candidate is evaluated only at its nominal TRAIN context.

### Bastion robust repertoire evolution

Each candidate is evaluated at:
- the nominal TRAIN context; and
- a frozen local training uncertainty halo.

Candidate score is based on the worst feasible halo utility. Any candidate infeasible at any required halo point is robust-infeasible for that source niche.

The archive therefore stores elites selected for local robustness during evolution rather than filtering nominal elites after evolution.

## Frozen training halo

For each TRAIN context:

```text
confidence shocks = [0.00, 0.02]
latency shocks    = [0.00, 0.08]
cost shocks       = [0.00, 0.08]
```

Cartesian product: up to 8 deterministic points.

The held-out selector uses the same target-feasible nominal selection rule for both arms. This isolates search-time robustness.

## Budget accounting

A raw candidate evaluated on 8 halo points costs 8 policy-context evaluations.

Search budgets are matched on total policy-context evaluations, not population steps.

Therefore the nominal arm receives more candidate proposals when necessary to match total evaluation cost fairly.

## Primary endpoint

For each seed:

```text
WorstBastion(seed) =
  min actual-target utility over HELD_OUT contexts
  using Bastion-evolved repertoire

WorstNominal(seed) =
  min actual-target utility over HELD_OUT contexts
  using nominally evolved repertoire

DeltaWorst(seed) =
  WorstBastion(seed) - WorstNominal(seed)
```

Primary support requires a positive paired bootstrap interval while the candidate passes the frozen safety gate.

## Secondary endpoints

- robust archive coverage on TRAIN/DEVELOPMENT;
- VSR/FCR/UAR;
- evidence-integrity failures;
- selection failures;
- recovery rate;
- human interventions;
- CPVO;
- aggregate latency;
- mean actual-target utility;
- candidate proposals consumed per arm;
- total policy-context evaluations per arm.

## Scientific boundary

JAR-EXP-0017 HELD_OUT data may motivate this mechanism but may not be reused as JAR-EXP-0018 confirmatory evidence.

JAR-EXP-0018 uses a new frozen context manifest and new held-out outcomes.

No production or real-agent claim is created by this study.
