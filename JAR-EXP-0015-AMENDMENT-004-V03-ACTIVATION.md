# JAR-EXP-0015 Amendment-004 — Dataset v0.3 activation under protocol v0.4

**Date:** 2026-09-19  
**Status:** FROZEN_PREEXECUTION  
**Trigger:** Amendment-003 precondition satisfied — deterministic projection and label-leakage tests pass

## Finding

Amendment-003 declared dataset v0.2 non-execution-eligible because the canonical System One state projection hid decision-relevant semantics: only `scenario` survives projection, and v0.2 stored its useful semantics in `archetype` and `signal`. Amendment-003 froze dataset v0.3, which encodes all decision-relevant semantics in the already-allowed `scenario` field, and required a new protocol activation after two deterministic tests pass.

Both preconditions are now verified deterministically (zero network, zero provider calls):

1. **Projection visibility.** `project_decision_state()` accepts all 3,904 v0.3 states. Every projected state is exactly `{"scenario": ...}`; no decision type is rejected and `project_decision_state()` is not widened.
2. **Label leakage.** No expected label token appears verbatim in any `scenario`. Across all eight decision types, verbatim label leaks = 0.

## Correction

Protocol **v0.4** activates dataset **v0.3**:

- rebinds `dataset_ref` / `split_manifest_ref` to the frozen v0.3 artifacts and their SHA-256 values;
- preserves every v0.3 protocol rule: threshold/promotion rules, the four arms, the authority boundary, sample-size feasibility, and the zero-network state;
- records amendments 001, 002, 003.

The active-protocol registry, calibration gate, hold-out gate, and analysis gate are rebound to protocol v0.4 / dataset v0.3. Frozen v0.3 artifact hashes:

- `data/jar_exp_0015_dataset_v03.json` — `51846d8b4a95540a8e182a823a7256fbdd69d61b3244f89e078db77ad7e0496e`
- `data/jar_exp_0015_split_manifest_v03.json` — `46b0123ed31b27d80823e518bef9e24bf4f1cc672f763d7b75e446698a00b745`

## Scientific status

- protocol v0.1: superseded — sample size mathematically infeasible before execution;
- protocol v0.2: superseded — coverage integer-rounding metadata corrected before activation;
- protocol v0.3 + dataset v0.2: superseded-before-execution — provider projection hid decision-relevant semantics;
- protocol v0.4 + dataset v0.3: **active, execution-eligible**, pending semantic review, owner approval, and budget authorization.

No JAR-EXP-0015 provider call has occurred under any superseded version. This amendment authorizes no network calls; `network_calls_authorized` remains false in every gate.
