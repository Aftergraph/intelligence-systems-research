# Aftergraph Jev Engineering v2.14.0

## Heterogeneous governed subagents

- Adds backend registry identities for local, provider, and Aftergraph worker execution surfaces.
- Adds capability + competence-aware deterministic routing.
- Adds AUTO/HIERARCHICAL/PARALLEL topology selection without changing authority semantics.
- Adds signed per-subagent execution receipts binding backend identity, trace/span, input/output digests, tool attestations, provider request lineage, and live-evidence status.
- Live-provider evidence fails closed unless the backend is authenticated HTTPS, request lineage is present, evidence origin is `live-provider`, and a persistent signing key is used.
- Synthetic/local/ephemeral-key execution can be cryptographically signed but never becomes live-provider evidence.
- 24/24 dedicated v2.13 heterogeneous/public-API tests PASS before full regression.

## Truth boundary

`authenticated_live_ab_executed=false`; `live_provider_measurement=false`; `measured_10x=false`.

# Aftergraph Jev Engineering v2.12.0

## Frontier

Governed multi-agent execution: hierarchical orchestration with bounded parallel fan-out/fan-in, least-privilege context/tool scopes, explicit dependency-output contracts, evaluator gates, retry/fallback/circuit-breaker recovery, structured traces, and deterministic join semantics.

## Verification

- 329/329 tests PASS across six isolated shards.
- 39/39 v2.12 dedicated multi-agent/public-API tests PASS.
- `compileall`: PASS.
- Secret scan: PASS.
- Release relocatability: PASS.
- Wheel build/import: PASS.
- Installed-wheel `v212-demo`: PASS.

## Truth boundary

`v212-demo` uses deterministic local adapters only. It demonstrates orchestration semantics, not provider-backed subagents and not a measured efficiency improvement.

- `authenticated_live_ab_executed=false`
- `live_provider_measurement=false`
- `measured_10x=false`
- historical `11.86x` remains modeled, not measured.