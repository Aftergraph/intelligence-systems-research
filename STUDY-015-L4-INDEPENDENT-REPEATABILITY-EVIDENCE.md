# STUDY-015 — L4 Independent Repeatability Evidence

**Study:** STUDY-015  
**Checkpoint:** L4 Independent Repeatability  
**Status:** VERIFIED L4 INDEPENDENT REPEATABILITY  
**Recorded:** 2026-09-25  
**Evidence class:** `L4_INDEPENDENT_REPEATABILITY_CANDIDATE`

## Result

A second bounded live composition completed successfully using the same pinned owner implementations but **fresh causal identity and a fresh exact verification subject**.

The final type-strict run was GitHub Actions run `36112014456` from Runtime PR `#205`. The earlier L4 run was superseded and is not the canonical checkpoint.

## Frozen provenance

- Runtime runner PR: `#205`
- Runtime runner head: `54c2e69d6ee81df51b5ab451dfbf16b8be86acb3`
- STEWARD L4 PR: `#45`
- STEWARD L4 head: `16f1a2a26d5cdd37937b5c25d113f1f6e9ba07c9`
- Proof-target PR: `#204`
- Workflow run: `36112014456`
- Artifact ID: `10853881273`
- Artifact ZIP SHA-256: `048d09bc8c2193b2ef208b5360f6fd78768cda5ef4eb3f8f9cc558a9be29801b`
- L4 causal receipt SHA-256: `31d734b5a958f13a4a9db8306f8fefa4e147dc26a066d78df4fea1ed0fd28e96`

The machine-readable source of truth is `data/study015/l4_repeatability.json`.

## Fresh identity

L4 deliberately did not reuse the L3 causal identity:

- mission: `mis_study015_l4_repeatability`
- work: `wrk_2dc7e8b8d0da70116bcf321c3f5f6dac`
- worker lease: `lse_36f8504ef3da15e61d9915f3bf7b0a65`
- runtime dispatch: `rdisp/e7103c6b18918486`
- WORKS execution: `wexec/idem/study015/live-2`
- execution context: `ctx_702c5632e8329dff16124ffe514b1367`
- trace: `trc_3df32192693662c44a94dc61bdc78ce0`
- action: `act_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb`
- execution PDR: `pdr_e64f5e97ee7668fec63ef8dfb3f1e944`
- effect: `effect/study015/live-2`
- causal ID: `causal/study015/live-2`
- exact verification subject: `git:Aftergraph/runtime@7dc0a336e06e7528f471bbd5676ddb50df6e9046`

The Runtime proof target was independently read back at exactly the same SHA.

## Repeatability falsification

The final runner required each `fresh_*` value to be the boolean value `true`, not merely truthy.

Verified fresh dimensions:

1. action identity;
2. causal identity;
3. effect identity;
4. exact verification subject;
5. execution context;
6. mission identity.

The receipt also binds its predecessor to:

- L3 causal receipt: `39a4e862030476ad4585fd70038056c8ad3e2b719e645ca64b86a477cdfb230d`
- L3 execution context: `ctx_c25bcc01cd7b21ed26826f1666847208`

A deliberate attempt to use that frozen L3 execution context in the L4 MissionAcceptance was rejected.

## Hostile checks

All L4 hostile paths passed:

- prior L3 execution-context replay rejected;
- wrong execution PDR rejected;
- stale verifier head rejected;
- revoked authority rejected before Git egress.

All eleven L3 composition seams also remained true in L4.

## What L4 establishes

L4 provides stronger evidence than L3 that the composition result was not dependent on reusing the first run's execution identity or proof subject.

It demonstrates repeatability for the tested pinned implementation and environment. It does **not** establish statistical repeatability, generalization to arbitrary implementations, production correctness, or comparative performance.

## Claim boundary

L4 still explicitly records:

- `performance_claim = false`
- `g15_9_authorized = false`
- `production_deployment = false`
- no world-first claim
- no industry-superiority claim

## Next frontier candidate — L5 durable causal recovery

The next systems gate should test causal continuity across controlled failure rather than immediately benchmarking speed.

A useful L5 experiment would interrupt the chain after the governed remote effect but before independent verification/MissionAcceptance, restart the relevant process boundary, and require:

1. recovery of the exact execution context and exact effect subject from durable state;
2. no duplicate remote effect;
3. fresh authority revalidation after restart;
4. exact-head independent verification against the original effect;
5. idempotent MissionAcceptance retry;
6. rejection of stale/prior causal identity;
7. preservation of the no-authority-expansion and no-self-verification invariants.

This remains a conformance/durability frontier. It does not authorize G15-9.
