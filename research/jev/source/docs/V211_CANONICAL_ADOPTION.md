# v2.11 canonical adoption boundary

Jev Engineering is research/evaluation infrastructure. Under Aftergraph governance, research programmes, benchmarks, experiments, papers, and reference runtimes belong to `Aftergraph/intelligence-systems-research`.

v2.11 therefore treats that repository as the canonical adoption target. It does **not** move AIE authority semantics, Trust Gateway admission, WORKS durable execution, or Sentinel verification ownership into Jev.

## Claim boundary

The release contains a deployable authenticated provider-lineage benchmark path, but the build environment has no live provider credentials. Consequently:

- `authenticated_live_ab_executed = false`
- `live_provider_measurement = false`
- `measured_10x = false`
- the historical 11.86x result remains modeled, not experimentally measured.

A future live result is admissible only if the paired campaign runs through `live-campaign-v210` (or a compatible successor), provider request lineage is present, the evidence bundle verifies against the persistent public key, and the deterministic benchmark verifier passes.

## v2.11 release hardening

v2.11 adds a relocatability gate so shipped evidence cannot retain stale build-container paths, aligns user-visible/package versions, and requires immutable SHA pins for external GitHub Actions used by shipped workflows.
