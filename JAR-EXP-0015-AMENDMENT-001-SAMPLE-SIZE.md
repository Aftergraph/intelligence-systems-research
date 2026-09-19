# JAR-EXP-0015 Amendment-001 — Sample-size feasibility correction

**Date:** 2026-09-19  
**Status:** FROZEN_PREEXECUTION  
**Trigger:** deterministic falsification before any JAR-EXP-0015 provider inference

## Finding

Protocol v0.1 specified 24 calibration + 16 hold-out cases per decision type while also requiring a Wilson 95% upper accepted-error bound ≤ 0.05 for every promoted decision class.

That design is mathematically incapable of satisfying its own per-class rule:

- with 0 errors, minimum accepted N for Wilson upper ≤ 0.05 is **73**;
- with 1 error, minimum accepted N is **110**;
- with 2 errors, minimum accepted N is **142**.

Therefore:
- calibration N=24 can never produce a feasible per-class threshold, even at 0 errors;
- hold-out N=16 can never validate a promoted per-class policy, even at 0 errors.

This was found **before any JAR-EXP-0015 live/model inference**. No empirical outcome motivated the amendment.

## Correction

Protocol v0.2 uses, per decision type:
- **244 calibration cases**
- **244 hold-out cases**
- **488 total**

Across 8 decision types:
- **1,952 calibration**
- **1,952 hold-out**
- **3,904 total**

Why 244:
- 30% of 244 = 73.2;
- thus the preregistered 30% coverage floor can yield at least 73 accepted cases;
- 73 accepted cases with zero errors is the first N for which the frozen Wilson upper bound is ≤0.05.

The 5% Wilson rule, 30% coverage floor, and zero critical-error rule are unchanged.

## Scientific status of v0.1

v0.1 remains preserved as a **falsified pre-execution design artifact**. It is not admissible for execution.

No v0.1 case has been sent to TypeSafe or any other model for JAR-EXP-0015.

## Non-changes

This amendment does not change:
- hypotheses H1–H4;
- decision types;
- initially revision-eligible classes;
- authority boundaries;
- model/provider choice;
- threshold selector;
- critical-risk rule;
- hold-out non-use requirement;
- NO_PROMOTION outcome;
- zero-network status.

## Activation

Only protocol/dataset/split-manifest **v0.2** may become execution-eligible after:
1. deterministic generator validation;
2. parent duplicate/leakage checks;
3. exact-head CI;
4. model/pricing/cost freeze;
5. independent semantic falsification review;
6. new explicit owner/network approval.

This amendment authorizes no live calls.
