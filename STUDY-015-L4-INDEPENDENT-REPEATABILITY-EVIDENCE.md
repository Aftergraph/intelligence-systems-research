# STUDY-015 — L4 Independent Repeatability Evidence

**Study:** STUDY-015  
**Checkpoint:** L4 Independent Repeatability  
**Status:** VERIFIED L4 INDEPENDENT REPEATABILITY  
**Recorded:** 2026-09-25  
**Evidence class:** `L4_INDEPENDENT_REPEATABILITY_CANDIDATE`

## Result

A second bounded live composition completed successfully using the same pinned owner implementations as L3 but with **fresh causal identity and a fresh exact verification subject**.

The canonical run is GitHub Actions run `36166670115` from Runtime PR `#205`. Earlier L4 runs are superseded and are not canonical evidence.

## Frozen provenance

- Runtime runner PR: `#205`
- Runtime runner head: `67845eaa6dd0c1a84726d784fed779e663c37187`
- STEWARD L4 PR: `#45`
- STEWARD L4 head: `8d0fc1141f75436fc2f969d0f2e8359807c7b130`
- Proof-target PR: `#204`
- Workflow run: `36166670115`
- Artifact ID: `10877243342`
- Artifact size: `1435` bytes
- Artifact ZIP SHA-256: `5be5f38d76e6a25255a2893fa59703b234fc6dab01432e51fe12a515465133ee`
- L4 causal receipt SHA-256: `3ae010a18e036d7978b06f85c783b21be724776ce9c2947fee93813d17d47e4c`

The machine-readable source of truth is `data/study015/l4_repeatability.json`.

## Fresh identity

L4 deliberately did not reuse the L3 causal identity:

- mission: `mis_study015_l4_repeatability`
- work: `wrk_9afa96093d0fac89bd0b26bb1ffbecf0`
- worker lease: `lse_ffb4c3984e8be1f17b53fde141832b9f`
- runtime dispatch: `rdisp/e7103c6b18918486`
- WORKS execution: `wexec/idem/study015/live-2`
- execution context: `ctx_243e1bc1627b3ce8167df39c791e3f6e`
- trace: `trc_ce36d2c69d76c07f8b6a21c8c22e05ac`
- action: `act_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb`
- execution PDR: `pdr_0610444fd035d6c72b5a310b3798418f`
- effect: `effect/study015/live-2`
- causal ID: `causal/study015/live-2`
- exact verification subject: `git:Aftergraph/runtime@92cc08482d91d70140db4916f1a11fc43b6318f6`

The L4 proof target was independently read back at exactly `92cc08482d91d70140db4916f1a11fc43b6318f6`.

## Repeatability falsification

L4 was pinned to the verified L3 predecessor:

- L3 causal receipt: `39a4e862030476ad4585fd70038056c8ad3e2b719e645ca64b86a477cdfb230d`
- L3 execution context: `ctx_c25bcc01cd7b21ed26826f1666847208`
- L3 exact subject: `git:Aftergraph/runtime@9c781f624bae36ee35aa23df57060e934d3a634c`

The final workflow required every repeatability flag to be strict boolean `true`:

1. fresh action ID;
2. fresh causal ID;
3. fresh effect ID;
4. fresh exact subject;
5. fresh execution context;
6. fresh mission ID;
7. rejection of the prior L3 execution context.

A deliberate attempt to bind the frozen L3 execution context into the L4 MissionAcceptance returned the expected fail-closed conflict.

## Hostile checks

All hostile paths passed:

- prior L3 execution-context replay rejected;
- wrong execution PDR rejected;
- stale verifier head rejected;
- revoked authority rejected before Git egress.

All eleven L3 composition seams remained true in L4.

## Claim boundary

L4 supports a narrow repeatability claim for the tested pinned implementation and environment. It does **not** establish statistical performance, arbitrary-environment correctness, production readiness, industry superiority, uniqueness, or external reproduction.

The receipt explicitly records:

- `performance_claim = false`
- `g15_9_authorized = false`
- `production_deployment = false`

## Next frontier candidate — L5 durable causal recovery

The next systems gate should interrupt the verified chain **after the governed remote effect but before independent verification/MissionAcceptance**, restart the relevant process boundary, and require:

1. recovery of the exact execution context and effect subject from durable state;
2. no duplicate remote effect;
3. fresh authority revalidation after restart;
4. exact-head verification against the original effect;
5. idempotent MissionAcceptance retry;
6. rejection of stale/prior causal identity;
7. no authority widening and no self-verification.

L5 remains conformance/durability research. It does not authorize G15-9.
