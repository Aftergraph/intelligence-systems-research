# JAR-EXP-0017 — VERGE Halo

**Title:** Robust Repertoire Selection Under Context Uncertainty  
**Status:** DESIGN / PREREGISTRATION DRAFT  
**Parent evidence:** JAR-EXP-0016 frozen HELD_OUT result  
**Canonical owner:** Aftergraph/intelligence-systems-research

## Trigger

JAR-EXP-0016 did not support its preregistered superiority hypothesis even though the repertoire won 29/30 seeds and passed the safety gate.

The dominant loss was not an authority violation. It was a robustness failure:

```text
source elite remained target-feasible
but
confidence margin was too small for the shifted target's no-intervention threshold
```

This creates a new, narrower research question.

## Hypotheses

**H0-HALO:** Robust neighborhood-aware selection provides no reproducible improvement in worst-context verified utility over nominal nearest-feasible repertoire selection.

**H1-HALO:** With the same evolved repertoire and no extra search budget, selecting elites by robust performance across a frozen local uncertainty halo improves seed-level worst-context verified utility on held-out context shifts without increasing unauthorized actions or evidence-integrity failures.

**H2-HALO:** Any robustness benefit survives mean-utility and CPVO reporting rather than merely exchanging catastrophic tails for unacceptable average cost.

## Mechanism

Search is intentionally held constant.

Both candidate and comparator use the same fixed-operator context-conditioned repertoire.

Only selection changes.

### Nominal selector

```text
target context
→ filter target-infeasible elites
→ nearest descriptor
→ tie-break by target utility
```

### Halo selector

```text
target context
→ construct frozen local uncertainty neighborhood
→ filter elites infeasible at nominal target
→ require feasibility across every halo point
→ rank by worst-case halo utility
→ tie-break by mean halo utility
→ then descriptor distance
→ fail closed if none survive
```

## Frozen uncertainty halo

For each target context, evaluate each candidate under the Cartesian product:

```text
min_confidence shock:  +0.00, +0.02, +0.04
latency_pressure shock: +0.00, +0.10
cost_pressure shock:    +0.00, +0.10
```

Values are clipped to their valid bounds.

This creates up to 12 deterministic halo points per target.

The +0.04 confidence shock is motivated by the JAR-EXP-0016 failure mode and the evaluator's no-intervention margin. It is frozen before JAR-EXP-0017 outcome evaluation.

## Primary endpoint

For each search seed, compute:

```text
WorstContextUtility(selector) =
  min utility over frozen HELD_OUT contexts

DeltaWorst(seed) =
  WorstContextUtility(Halo)
  - WorstContextUtility(Nominal)
```

Primary support requires the 95% paired bootstrap CI of DeltaWorst to lie strictly above zero.

## Secondary endpoints

- mean held-out utility;
- VSR;
- FCR;
- UAR;
- evidence-integrity failures;
- selection failures;
- recovery rate;
- CPVO;
- aggregate latency;
- human-intervention count;
- robust-selection evaluation overhead.

## Search budget

Halo and nominal arms reuse the **same** evolved repertoire for each seed.

Therefore their evolutionary search budget is exactly identical by construction.

Only selector evaluation overhead differs and is reported separately.

## Evidence boundary

This is a new experiment ID.

No JAR-EXP-0016 held-out observation may be reused as JAR-EXP-0017 confirmatory evidence.

The JAR-EXP-0016 failure may motivate the mechanism, but JAR-EXP-0017 requires a new frozen context set and new held-out outcomes.

## Prior-art anchors

- Yadav, Ramu & Deb (2025), robust multi-objective optimization and decision-making under variable uncertainty, DOI 10.1016/j.swevo.2025.101860.
- Jiang et al. (2025), robust multi-objective evolutionary optimization under input disturbance, DOI 10.1007/s40747-025-01822-y.
- Qin et al. (2026), Quality-Diversity survey, DOI 10.1016/j.swevo.2025.102240 — uncertainty/robustness is identified as an active QD research direction.
- Flageat et al., GECCO 2025, Extract-QD — modular uncertain-QD framework for noisy, stochastic and uncertain domains.

These sources support robustness-under-uncertainty as an established problem class. They do not validate VERGE Halo.
