# Jev Engineering research adoption

Jev Engineering is research/evaluation infrastructure owned by `Aftergraph/intelligence-systems-research` under the canonical repository registry.

This adoption record does **not** transfer authority, admission, durable execution, or independent verification ownership into Jev. Those boundaries remain with AIE, Trust Gateway, WORKS, and Sentinel respectively.

## Current release

- Release: `2.11.1`
- Release ZIP SHA-256: `bdc7889921b109d2911e75d849fd9874b36c18b55e14fd2bd3f2afcbbbeff981`
- Wheel SHA-256: `c1dc4a9376e62b7b646b8f618d001a45d86cfeddcb981598d61a10c4e7a8e430`
- Tests: `290/290 PASS`
- Release relocatability gate: `PASS`
- Secret scan: `PASS`
- Canonical source: `research/jev/source`

## Claim boundary

No authenticated provider-backed A/B campaign was executed in the build environment.

```text
authenticated_live_ab_executed = false
live_provider_measurement = false
measured_10x = false
historical_11_86x = modeled_not_measured
```

A future performance result is admissible only when provider request lineage is present, the signed evidence bundle verifies against the persistent public key, and the deterministic paired benchmark verifier passes.

## Adoption state

v2.11.1 is mechanically materialized in this repository as canonical research source. The import evidence is recorded under `research/jev/import/v2.11.1/evidence.json`. The release artifact remains separately sealed by the exact ZIP and wheel hashes above.
