# Jev Engineering research adoption

Jev Engineering is research/evaluation infrastructure owned by `Aftergraph/intelligence-systems-research` under the canonical repository registry.

This adoption record does **not** transfer authority, admission, durable execution, or independent verification ownership into Jev. Those boundaries remain with AIE, Trust Gateway, WORKS, and Sentinel respectively.

## Current release

- Release: `2.11.0`
- Release ZIP SHA-256: `fd0a357349d54c8670d9d2d8a4b872fecba924ba64758b1b43a70adac3c6ac12`
- Wheel SHA-256: `44e733b922796c8a10b5345d7bedab01a8c95cf789763f4a7095a5c4c7de76ed`
- Tests: `290/290 PASS`
- Release relocatability gate: `PASS`
- Secret scan: `PASS`

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

The v2.11 archive is the current handoff artifact. Source import into this canonical repository remains a separate mechanical migration step; this record establishes ownership, exact artifact identity, and claim boundaries without pretending the archive has already been imported.
