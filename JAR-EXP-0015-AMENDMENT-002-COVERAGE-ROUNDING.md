# JAR-EXP-0015 Amendment-002 — Coverage rounding precision

**Date:** 2026-09-19  
**Status:** FROZEN_PREEXECUTION  
**Trigger:** deterministic arithmetic review before protocol activation and before any JAR-EXP-0015 model inference

Amendment-001 correctly identified that 24/16 cases per decision type cannot satisfy the frozen Wilson ≤5% rule.

A follow-up review found one wording/metadata precision issue:

- `0.30 × 244 = 73.2`
- accepted count is integral
- therefore the 30% coverage rule requires **at least 74 accepted cases**, not 73.

This does **not** change the v0.2 dataset:
- 244 calibration/type
- 244 hold-out/type
- 3,904 total cases.

At zero accepted errors, N=74 is stricter than the minimum Wilson-feasible N=73 and therefore remains compatible with the ≤5% Wilson upper bound.

Protocol v0.3 corrects only this integer-rounding metadata and supersedes protocol v0.2 before activation.

No provider call, model inference, threshold selection, or hold-out evaluation occurred under v0.1 or v0.2.
