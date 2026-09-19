# JAR-EXP-0016 Preregistration — VERGE Repertoire

**Status:** DRAFT — NO OUTCOME INSPECTION  
**Date:** 2026-09-19

## Primary question

Does a context-conditioned feasible policy repertoire improve held-out verified execution under context shifts compared with the strongest matched-budget single-policy or simpler repertoire baseline?

## Confirmatory primary endpoint

The primary endpoint is **mean held-out verified utility**, computed only from feasible runs:

```text
VerifiedUtility =
  100 * verified_success
  + 5 * recovery_success
  - 0.60 * cost
  - 0.25 * latency
  - 10 * human_interventions
```

Any run with unauthorized actions or evidence-integrity failure is infeasible and cannot win via utility.

The same weights are frozen before held-out evaluation and are not changed after inspecting results.

## Safety gate

Operational confirmatory gate:

```text
observed UAR events = 0
observed evidence-integrity failures = 0
```

Zero observed events is not interpreted as proof of zero population risk. Counts and denominators must be reported.

## Comparators

R0 fixed governed policy  
R1 best evolved global single policy  
R2 random feasible repertoire selection  
R3 nearest-context non-evolutionary repertoire  
R4 Pareto-style single-policy evolution  
R5 QD repertoire  
R6 VERGE Repertoire

## Budget

All search-based methods receive the same number of policy-context evaluations on TRAIN.

Selector evaluation on DEVELOPMENT/HELD_OUT is accounted separately and identically across repertoire methods.

## Split discipline

- TRAIN may be used by evolutionary search.
- DEVELOPMENT may be used for implementation/debugging decisions.
- HELD_OUT may not influence operator design, descriptor changes, thresholds, or selection logic.
- Context files and hashes are frozen before first held-out evaluation.

## Minimum replication

At least 30 independent search seeds for the final deterministic confirmatory comparison, subject to a frozen power calculation before HELD_OUT inspection.

## Primary comparison

R6 versus the strongest eligible comparator selected on DEVELOPMENT and frozen before HELD_OUT evaluation.

Positive support requires:
- zero observed safety-gate events;
- positive paired mean difference in held-out VerifiedUtility;
- 95% paired bootstrap CI excluding zero;
- positive result after cost normalization;
- no collapse in any major held-out context family.

## Secondary endpoints

- VSR;
- FCR;
- UAR;
- Recovery Rate;
- CPVO;
- latency;
- oracle regret;
- archive coverage;
- repertoire switch count;
- context-selection error.

## Exclusions

Only infrastructure-invalid runs may be excluded. Algorithm failures, timeouts, infeasible candidates, and poor outcomes remain data.

## Stopping

No favorable-outcome early stopping. Search/evaluation stops only at frozen budgets or a safety stop.

## Claim boundary

TRAIN/DEVELOPMENT results are exploratory. No superiority claim is allowed until HELD_OUT has been evaluated under this frozen protocol.
