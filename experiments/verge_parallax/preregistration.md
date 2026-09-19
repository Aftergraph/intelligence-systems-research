# JAR-EXP-0021 Preregistration — VERGE Parallax

**Status:** FROZEN INTERNAL REPLICATION  
**Date:** 2026-09-19

## Input evidence

Parent experiment:
`JAR-EXP-0020`

Parent frozen raw result:
`data/verge_headroom_heldout_confirmatory_v1.json`

Parent SHA-256:
`11e6c0d4e66584f407e7e784b65afe9f985d12478cc3016e2dc559131b83bc4c`

## Replica implementation restriction

The replica source file may not import:
`experiments.verge_headroom.ranking`.

## Frozen reproduction requirement

For seeds 0..29 and the frozen JAR-EXP-0020 candidate budget:

- replica Headroom selection identity must equal original selection identity for every TRAIN niche;
- replica HELD_OUT seed delta vector must exactly equal the parent vector;
- summary scalars must match within floating-point serialization equality from the shared evaluator;
- safety verdict must match.

Any mismatch is retained as a failed replication result.

## Evidence level

INTERNAL_IMPLEMENTATION_REPLICATION.

No external-reproduction claim is permitted.
