# JAR-EXP-0019 — VERGE Crucible

**Title:** Multi-Fidelity Robust Repertoire Evolution  
**Status:** DESIGN / PREREGISTRATION DRAFT  
**Parent evidence:** JAR-EXP-0018 DEVELOPMENT falsification

## Trigger

JAR-EXP-0018 showed that evaluating every candidate across an 8-point robustness halo is too expensive under a matched total policy-context budget: robust search saw one eighth as many candidates and lost on DEVELOPMENT.

JAR-EXP-0019 tests a multi-fidelity alternative.

## Core idea

Spend most of the budget on cheap nominal exploration.

Promote only the strongest nominally feasible candidates to expensive robust evaluation.

```text
broad nominal proposals
→ nominal feasibility + utility screen
→ promotion gate
→ remaining halo evaluations
→ robust elite selection
```

## Hypotheses

**H0-C:** Multi-fidelity promotion does not improve worst-context verified utility versus nominal repertoire search under the same total policy-context budget.

**H1-C:** Multi-fidelity robust promotion improves DEVELOPMENT and then HELD_OUT worst-context verified utility without increasing observed UAR or evidence-integrity failures.

**H2-C:** Crucible achieves higher robust archive coverage than nominal search while retaining substantially more proposal diversity than full-halo Bastion.

## Frozen per-niche budget

```text
total policy-context budget = 256

CRUCIBLE:
  144 nominal candidate evaluations
  16 promoted candidates
  7 additional halo evaluations per promoted candidate
  144 + (16 * 7) = 256

NOMINAL:
  256 nominal candidate evaluations
```

The halo has 8 total points; nominal evaluation supplies the zero-shock point.

## Primary endpoint

Same family as prior studies:

```text
DeltaWorst(seed) =
  min actual-target utility(Crucible repertoire)
  -
  min actual-target utility(Nominal repertoire)
```

## Scientific boundary

New context manifest. JAR-EXP-0017/0018 HELD_OUT outcomes are not reused as evidence.
