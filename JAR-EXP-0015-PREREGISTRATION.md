# JAR-EXP-0015 — Prospective Decision-Specific System One Calibration

**Status:** FROZEN_PREEXECUTION  
**Parent evidence:** JAR-EXP-0014 terminal calibration-negative result  
**Issue:** #122  
**Network calls authorized:** NO

## Research question

Does JAR-EXP-0014's `NO_THRESHOLD` outcome arise from heterogeneous calibration across decision types, from specific contract/state-projection weaknesses, or both?

JAR-EXP-0014 is immutable diagnostic evidence only. Its observations may shape hypotheses and test design, but they cannot be reused as JAR-EXP-0015 calibration or hold-out observations.

## Trigger evidence

JAR-EXP-0014:
- 158 observations
- 143 correct / 15 incorrect
- 3 critical-risk errors
- no feasible global threshold
- `risk_level`: 11/16 correct
- `route_model`: 13/16
- `result_sufficient`: 14/16
- `retryable_failure`: 16/16
- `route_tool_family`: 16/16

The high median confidence observed in some weak classes, especially `risk_level` and `route_model`, motivates a calibration-vs-contract falsification rather than a post-hoc threshold rescue.

## Hypotheses

- **H1 — Heterogeneous calibration:** confidence/error behavior differs materially across frozen decision classes.
- **H2 — Infeasible-class hypothesis:** at least one weak class remains infeasible under a class-specific threshold on new prospective calibration data.
- **H3 — Selective-cascade hypothesis:** excluding infeasible classes to deterministic fallback/escalation permits useful accepted coverage while preserving the frozen safety constraints.
- **H4 — Contract-revision hold-out hypothesis:** any revised contract must improve on a separately held-out prospective set; gains on JAR-EXP-0014 or the new calibration split alone are non-admissible for promotion.

## Prospective dataset

Create a new labeled corpus with exactly **320 cases**:
- 8 decision types × 40 cases each.
- Within each type: 24 calibration cases + 16 hold-out cases.
- split assignment frozen before any provider inference.
- all authority-sensitive/critical cases identified before inference.
- minimum 8 critical cases for each authority-sensitive class (`needs_human`, `risk_level`).
- case IDs and labels immutable after freeze.

JAR-EXP-0014 cases may be used only as examples for authoring *new* cases. Exact state/label duplicates are forbidden.

## Arms

- **A — Global frozen-contract baseline:** original JAR-EXP-0014 contracts, one global threshold.
- **B — Decision-specific threshold baseline:** original contracts, independently selected threshold per decision type.
- **C — Selective cascade:** original contracts; classes with no feasible threshold are forced to deterministic fallback/escalation.
- **D — Revised-contract candidate:** only for classes preregistered as weak; revised contract/state projection evaluated with separate calibration and hold-out data.

No arm may grant authority. System One outputs remain advisory.

## Threshold selection

Threshold candidates are the unique observed effective-confidence values plus 0 and 1.

For every thresholded class:
- minimum accepted coverage: **0.30**
- Wilson 95% upper bound on accepted error rate: **≤ 0.05**
- incorrectly accepted critical-risk decisions: **0**
- threshold chosen: lowest feasible threshold, maximizing accepted coverage.
- if no threshold is feasible: class status = `NO_THRESHOLD`.

For Arm A the same rule is applied globally.
For Arm B/D it is applied separately per decision class.
Arm C may consume only classes with a feasible prospective threshold; all others must fallback/escalate.

## Promotion rules

A candidate may be promoted only if all hold:
1. Calibration-derived policy was frozen before hold-out evaluation.
2. Hold-out data were never used to select contracts or thresholds.
3. Zero incorrectly accepted critical-risk hold-out cases.
4. Hold-out accepted error Wilson upper bound ≤ 0.05 for every promoted decision class.
5. Aggregate accepted hold-out coverage ≥ 0.30.
6. No authority/truth/verification boundary is weakened.
7. Deterministic fallback remains available for every rejected/infeasible class.

If no arm satisfies these rules: `NO_PROMOTION`.

## Contract revision policy

Only `risk_level`, `route_model`, and `result_sufficient` are eligible for initial revision because they were preregistered from the parent diagnostic evidence.

A revision must:
- receive a new contract version/id;
- state the hypothesized failure mechanism;
- not encode calibration labels/examples from the target split;
- use only state fields allowed by a separately reviewed projection;
- be frozen before new provider inference.

## Analysis

Report per type and arm:
- N, correct, errors
- accepted N / coverage
- accepted error rate
- Wilson upper bound
- critical accepted errors
- threshold
- Brier score for Noul where applicable
- multiclass log-loss where a complete Choice/Score distribution is available
- expected calibration error using a frozen binning rule
- fallback/escalation rate

Primary decision is feasibility/safety, not raw accuracy.

## Stop rules

Stop and freeze evidence if:
- provider/model identity drifts;
- pricing/context contract drifts;
- hidden retries appear;
- labels/split/contracts mutate after freeze;
- budget/call ceiling cannot be enforced;
- hold-out leakage is detected;
- any authority boundary is widened.

## Financial/network gate

No live call is authorized by this preregistration.

Before execution, require:
- concrete model pin;
- frozen provider price/context spec;
- pre-request hard budget reservation;
- zero SDK retries;
- durable per-case checkpoint;
- exact-head semantic falsification verifier;
- content-addressed owner/network approval receipt.

## Non-goals

- rescuing JAR-EXP-0014.
- choosing a threshold from JAR-EXP-0014 after seeing outcomes.
- claiming universal Jev quality.
- granting System One authority.
- confirmatory claims without a prospective hold-out.
