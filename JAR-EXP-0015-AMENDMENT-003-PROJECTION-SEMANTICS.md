# JAR-EXP-0015 Amendment-003 — Provider-state semantic visibility

**Date:** 2026-09-19  
**Status:** FROZEN_PREEXECUTION  
**Trigger:** deterministic provider-boundary inspection before any JAR-EXP-0015 model inference

## Finding

Dataset v0.2 stores useful synthetic-case semantics in `archetype` and `signal`.

The existing canonical System One state projection intentionally allows only a narrow set of fields. For these synthetic JAR-EXP-0015 states, only `scenario` survives projection.

In v0.2, `scenario` is primarily a generic case identifier. Therefore the provider would not receive enough semantic information to answer the frozen decision correctly.

This makes dataset v0.2 **non-execution-eligible** despite its correct sample-size and split design.

## Correction

Dataset v0.3 preserves:
- 3,904 total cases;
- 244 calibration + 244 hold-out per decision type;
- the v0.2 split seed and assignment;
- threshold/promotion rules;
- authority boundary;
- zero-network state.

It changes only synthetic state construction:

1. all decision-relevant semantics are encoded in the already-allowed `scenario` field;
2. no new provider fields are authorized;
3. `project_decision_state()` is not widened;
4. expected labels are not embedded verbatim in the provider scenario;
5. exact parent duplicates remain forbidden.

## Scientific status

- dataset/protocol v0.1: superseded — sample size impossible;
- protocol v0.2: superseded — rounding metadata;
- dataset v0.2 / protocol v0.3: superseded-before-execution — provider projection hid relevant semantics;
- dataset v0.3 requires a new protocol activation after deterministic projection and label-leakage tests pass.

No JAR-EXP-0015 provider call has occurred under any superseded version.
