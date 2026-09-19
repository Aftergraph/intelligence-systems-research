# JAR-EXP-0016 — Preregistration Amendment 02

**Reason:** Pre-held-out hostile review found a selector safety gap  
**Held-out outcomes inspected before amendment:** NO  
**Date:** 2026-09-19

## Finding

The first repertoire selector ranked elites by descriptor distance and source-context utility.

That was insufficient for a governed dynamic setting because:

```text
feasible in source context
!=
feasible in target context
```

A source elite can become invalid after a context shift if the target raises verification, confidence, or recovery requirements.

## Safety correction

Selection is now fail-closed:

1. re-evaluate every candidate elite against the **target context**;
2. discard target-infeasible elites;
3. rank only the remaining target-feasible elites by descriptor distance and target-context utility;
4. if no target-feasible elite exists, raise `LookupError("no target-feasible elite")` rather than execute a candidate.

This does not widen authority or weaken any benchmark/verifier semantics.

## TDD evidence

The failure was captured first by two regression tests:

- nearest source elite is target-infeasible while a farther safe elite exists;
- no target-feasible elite exists.

Before the fix both tests failed. After the fix the focused repertoire suite passed:

```text
15 passed
```

## Development-output invariance

The 30-seed DEVELOPMENT pilot was rerun after the safety correction.

The resulting serialized evidence was byte-equivalent to the prior canonical DEVELOPMENT dataset:

```text
SHA-256
a8562c5c4ed6869be0d8319b94b8bdeefc343965242427215471580c489b82b0
```

Therefore the safety correction changed behavior only for previously untested unsafe target-shift cases and did not alter the recorded DEVELOPMENT outcomes.

## Held-out freeze

No HELD_OUT outcome has been evaluated.

The held-out primary candidate remains **VERGE Repertoire Core**, now with the target-feasibility gate as a mandatory safety invariant.

Any later change to selector semantics, context definitions, utility weights, safety thresholds, comparator identity, or operator distribution requires a new experiment ID or an explicit pre-outcome amendment.
