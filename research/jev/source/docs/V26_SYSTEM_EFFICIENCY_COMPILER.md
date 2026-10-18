# v2.6 System Efficiency Compiler

v2.6 moves the 10× research target from a control-plane-only question to a whole-system frontier-token planning problem.

## Why this exists

v2.5 proved a structural limitation: if generator tokens dominate a mission, removing frontier control tokens alone cannot reach a 10× frontier-intelligence-efficiency target. v2.6 therefore models mutually-exclusive frontier-token categories and bounded optimization levers that may act on context, generation, control, retries, verification, or escalation.

The compiler is intentionally a **planning mechanism, not performance evidence**. A projected ratio is not a measured ratio. Promotion still requires the paired holdout campaign introduced in v2.5.

## Core contracts

`FrontierWorkloadProfile/v1` contains measured or explicitly synthetic token-accounting categories. Categories must be mutually exclusive at the caller boundary.

`EfficiencyLever` declares:

- the categories it can reduce;
- a maximum reduction fraction per category;
- a conservative lower bound on quality retention;
- an evidence level: `hypothesis`, `modeled`, `observed`, or `benchmarked`;
- an implementation-complexity cost used during plan selection.

`SystemEfficiencyPlan/v1` records the selected mechanisms, projected category totals, projected ratio, evidence threshold, and a truth boundary that prevents projected savings from being presented as observed gains.

## Composition laws

Two levers that target the same token category compose multiplicatively:

```text
100 tokens
-50% lever A
-50% lever B
= 25 tokens, not 0
```

Quality retention does **not** assume independence. The compiler uses a conservative union-bound lower bound:

```text
retention >= 1 - Σ(1 - per_lever_retention)
```

This is deliberately stricter than multiplying optimistic success probabilities.

## Runtime primitives

### Adaptive Context Budgeter

Selects the smallest fresh context budget that preserves a requested fraction of candidate utility. It reuses the semantic garbage collector, so stale, dependency-invalidated, and exact duplicate chunks remain excluded before budgeting.

### Verified Early Exit

A frontier call may be skipped only if:

- a cheaper path is already verified;
- predicted VSR meets the required VSR;
- risk is below the configured no-call ceiling;
- assurance requirements are below the configured no-call ceiling.

Otherwise the gate fails closed to frontier execution.

### Retry Budget Optimizer

Retries are admitted sequentially only while their estimated incremental VSR gain per 1,000 frontier tokens remains above policy and the frontier-token budget is not exceeded. Later high-value retries cannot be cherry-picked after an earlier sequential retry is rejected.

## 10× attainable-region search

The compiler can answer two different questions:

1. **Observed-evidence region:** what ratio is reachable using only mechanisms whose evidence level is at least `observed`?
2. **Modeled region:** what ratio is mathematically reachable if modeled mechanisms work within their declared bounds?

The second is a research hypothesis generator, not a benchmark result.

The bundled `v26-demo` intentionally demonstrates a case where:

```text
observed-evidence 10× attainable = false
modeled 10× attainable          = true
```

That distinction is the primary v2.6 truth boundary.

## CLI

```bash
jev-one efficiency-plan-v26 \
  configs/v26-efficiency-profile.example.json \
  --levers configs/v26-efficiency-levers.example.json \
  --target-ratio 10 \
  --min-quality 0.97 \
  --min-evidence modeled

jev-one v26-demo
```

## Promotion boundary

A `SystemEfficiencyPlan` cannot promote itself. The plan must be implemented, then evaluated through identical paired workloads and the v2.5 holdout-only evidence gate. The performance claim belongs to the measured campaign, never to this compiler output.
