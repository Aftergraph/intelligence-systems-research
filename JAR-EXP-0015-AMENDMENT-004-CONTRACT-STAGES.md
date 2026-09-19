# JAR-EXP-0015 Amendment-004 — Contract-arm execution separation

**Date:** 2026-09-19  
**Status:** FROZEN_PREEXECUTION  
**Trigger:** execution-plan falsification before the first JAR-EXP-0015 provider call

## Finding

JAR-EXP-0015 preregistered a revised-contract Arm D for `risk_level`, `route_model`, and `result_sufficient`.

Running both original and revised contracts on the same 244 calibration cases for those three classes requires **732 additional provider calls**. The already approved A/B/C calibration scope is exactly **1,952 calls / $5.38**.

Splitting 244 cases between original and revised contracts would reduce each arm below the sample-size needed by the frozen Wilson/coverage rule and is therefore not admissible.

## Correction

The execution plan is separated without changing the approved A/B/C scope:

- **A/B/C calibration:** 1,952 frozen calibration cases, original contracts only.
- **D revised-contract calibration:** separate later protected stage for 3 × 244 = **732 calls**.
- worst-case Arm D calibration cost: **$2.015196**, rounded hard ceiling **$2.02**.
- Arm D receives **no network/spend authorization** from the current A/B/C approval.
- all original and revised contracts are frozen before the first JAR-EXP-0015 provider inference.

The same separation applies to hold-out. Hold-out remains separately protected.

## Scientific effect

This prevents:
- post-hoc contract writing after seeing A/B/C calibration outcomes;
- underpowered 122/122 contract splits;
- silent expansion of the user's approved 1,952-call/$5.38 scope.

No JAR-EXP-0015 provider call occurred before this amendment.
