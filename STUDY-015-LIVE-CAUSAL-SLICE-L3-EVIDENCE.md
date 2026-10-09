# STUDY-015 — LIVE_CAUSAL_SLICE L3 Evidence Checkpoint

**Study:** STUDY-015  
**Checkpoint:** LIVE_CAUSAL_SLICE / L3  
**Status:** VERIFIED L3 COMPOSITION CONFORMANCE  
**Recorded:** 2026-09-25  
**Evidence class:** `L3_COMPOSITION_CONFORMANCE_CANDIDATE`

## Result

One bounded same-causal execution was completed successfully across real process boundaries:

`WORKS HTTP → Runtime CLI → Trust Gateway HTTP → AIE execution-time revalidation → human approval → governed Git effect → exact remote SHA readback → Sentinel exact-head verification → Runtime/WORKS subject binding → WORKS MissionAcceptance → durable Verified Outcome`

The run completed successfully in GitHub Actions run `36108876350` from Runtime PR `#203`.

## Frozen provenance

- Runtime runner head: `85d7a8c1374c745db4dec5c828263b44ae1de8ce`
- Runtime owner: `7dc0a336e06e7528f471bbd5676ddb50df6e9046`
- WORKS owner: `ee04809f041cbc328ba024400f0f538cf48239c1`
- Trust Gateway owner: `bb224848cd540db701de783f44101aa95e914563`
- AIE owner: `bdb36512e57e1bb1f2ec05312d725827267eafc1`
- Sentinel owner: `4125f66b0c6d476966feb017ec7ddf3e22ec9459`
- STEWARD orchestrator: `de491d04b24ea86c23b68fb886c98d01f8fd3eea`
- Receipt artifact ID: `10852541022`
- Artifact ZIP SHA-256: `d3a068a131d4abf2783ca99fc3dcdd687e2857d04135239df2fa228792dbec13`
- Causal receipt SHA-256: `39a4e862030476ad4585fd70038056c8ad3e2b719e645ca64b86a477cdfb230d`

The machine-readable source of truth is `data/study015/live_causal_slice_l3.json`.

## Exact causal binding

The successful slice bound all of the following into one evidence receipt:

- mission: `mis_study015_live_causal`
- work: `wrk_7f8d49b9f1e446f4ab1cc8624e9ebf5c`
- worker lease: `lse_aa71427591fdeffc378bc5a3fd816960`
- runtime dispatch: `rdisp/a00e22c896e513cb`
- WORKS execution: `wexec/idem/study015/live-1`
- execution context: `ctx_c25bcc01cd7b21ed26826f1666847208`
- trace: `trc_02f70eb5d99d939157862dd6ddc33d28`
- action: `act_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`
- execution PDR: `pdr_cafffe063d64f0a260ad6ad75689b2b6`
- effect: `effect/study015/live-1`
- causal ID: `causal/study015/live-1`
- exact verification subject: `git:Aftergraph/runtime@9c781f624bae36ee35aa23df57060e934d3a634c`
- Sentinel receipt: `d9a2949baf9a7d30569f425a240be2576fc308eb4c1bc9994a7e8dc05b83575e`

Remote readback confirmed Runtime proof-target PR `#202` at exact head `9c781f624bae36ee35aa23df57060e934d3a634c`.

## Falsification results

All hostile seams in the L3 slice passed:

1. Wrong execution PDR was rejected by MissionAcceptance.
2. A stale Sentinel verification head was rejected.
3. Revoked authority was rejected before governed Git egress.
4. The proof ref remained unchanged after the revoked-action replay.

These results demonstrate fail-closed behavior for the tested path. They do not establish universal correctness outside the tested composition.

## Claim boundary

This checkpoint supports a narrow claim:

> The pinned Aftergraph owner candidates demonstrated one live, network-using, same-causal composition path in which bounded authority, execution, exact effect identity, independent exact-head verification, MissionAcceptance and durable Verified Outcome remained causally bound, while the tested stale/revoked/mismatched hostile paths failed closed.

It does **not** establish:

- comparative performance improvement;
- lower cost, latency or control-plane tax;
- G15-9 authorization;
- production deployment status;
- industry superiority, uniqueness or a world-first claim;
- independent external reproduction.

## Next gate candidate — L4 independent repeatability

The next technical gate should test whether the L3 invariant chain survives repetition without reusing the first run's identity.

Minimum L4 conditions:

1. Generate fresh mission/work/lease/dispatch/context/trace/action/PDR/effect/causal identifiers.
2. Use a fresh exact proof subject rather than accepting the L3 subject.
3. Execute the same cross-owner chain from exact pinned heads.
4. Produce a second independently hashable causal receipt.
5. Verify that replaying L3 identity into L4 fails closed.
6. Verify stale verifier subject and revoked authority again.
7. Compare the two receipts only for invariant-equivalent structure, not performance.
8. Preserve `performance_claim=false`, `g15_9_authorized=false`, and `production_deployment=false`.

Only after repeatability and identity-isolation are established should a separately preregistered performance experiment be considered.
