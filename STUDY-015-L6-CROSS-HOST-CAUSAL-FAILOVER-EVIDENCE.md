# STUDY-015 — L6 Cross-Host Causal Failover Evidence

**Study:** STUDY-015  
**Checkpoint:** L6 Cross-Host Causal Failover  
**Status:** VERIFIED L6 CROSS-HOST CAUSAL FAILOVER  
**Evidence class:** `L6_CROSS_HOST_CAUSAL_FAILOVER_CANDIDATE`

## Result

The verified L5 durable composition was extended across a physical-host boundary.

Host A committed exactly one governed external Git effect, then exported a narrowly allowlisted, hash-bound, secret-free durable handoff. Host B ran on a different physical machine, verified the immutable handoff, re-issued fresh local secrets, reopened WORKS at a different host-local database path, recovered the same causal identity, verified the transferred Trust Gateway audit chain, revalidated authority without another effect, obtained an independent exact-head Sentinel verdict and committed MissionAcceptance.

Canonical execution is split across two immutable workflow records:

- **Host A:** Runtime run `36180579530`, job `108221643076`
- **Host B:** Runtime run `36182956767`, job `108229711916`

## Physical host separation

Host A:

- runner: `vds-aftergraph-ci-runtime`
- hostname: `vmi3517816`
- machine-id SHA-256: `f39a48b5cd616819f99f80e274f00fc46ac548d8c9ef83537f8e1b6e66644adc`

Host B:

- runner: `vps-ci-01`
- hostname: `vps-70333b3c`
- machine-id SHA-256: `f24637e0fe93a44ef6be6cb3fda4ea96855497c4e6b73fe5b1b95754cb1228db`

Both hostname and machine-id fingerprints differ. The receipt fails if either physical-host invariant is false.

## Immutable handoff

Host A produced:

- phase-A manifest SHA-256: `0f1acd4e1ebabe9571ddffbcf018ef2db948862c87d38eef4b49e072ddc0a6ea`
- handoff tar SHA-256: `27704eee7a694fbafb4bbbd4f4e150907b4c953c087c55e45946ed6950c21db1`
- artifact ID: `10884830989`
- artifact digest: `sha256:56b4ede8036424e063e5259ad9663175a3ae404cb5939752939a859c3151f2fc`

The allowlist carried only durable WORKS/AIE state, the WORKS fixture receipt, the append-only TG audit chain and phase-A metadata. GitHub credentials, TG vault/master material, API tokens and approval tokens were not transferred.

Host B verified the artifact metadata, tar hash, phase-A hash and per-file hashes before recovery. Secrets were generated fresh on Host B.

## Same causal identity after relocation

- mission: `mis_study015_l6_cross_host`
- work: `wrk_0fb3186b1ce15c36fd7ca3add10c5df6`
- WorkerLease: `lse_31b852e8ec2032714e563fcf1893215a`
- Runtime dispatch: `rdisp/21e8155383f3a465`
- WORKS execution: `wexec/idem/study015/live-4`
- execution context: `ctx_45a494a4d6bdf6897ac0f56d8ee55f14`
- trace: `trc_e4371a67c117ea5a4701f69db4fb364e`
- action: `act_dddddddddddddddddddddddddddddddd`
- execution PDR: `pdr_2bd82f02ee0eb50f06b97f174f22afd3`
- effect: `effect/study015/live-4`
- causal ID: `causal/study015/live-4`

Exact subject:

`git:Aftergraph/runtime@0c280233565ba5c98d259679ba5ef6a2663b8283`

Sentinel receipt:

`2e753bc026351d09a7e524a4cfad7a7db1e25fd250e5165ba565762390c56454`

L6 causal receipt SHA-256:

`0a1cc344c21becf0276cf41598943b6abd72ffd58bfb95f9e6c7369e1af3a8ff`

Host B receipt artifact:

- artifact ID: `10885480591`
- artifact digest: `sha256:e82ce37407c33351c5e37f394cd6ce87676b386191406f26fa75d57532d8a127`

## Cross-host invariants

All were strict true:

- different physical machine identity;
- different hostname;
- same Work;
- same execution context;
- same trace;
- same WORKS execution;
- exactly one external Git effect;
- durable Verified Outcome.

The research-only WORKS relocated recovery mode remained opt-in. A DB-path mismatch still fails closed unless explicit relocation is requested, and the recovered Work/WorkerLease identities are re-read from the durable database.

## Hostile checks

All passed:

1. wrong execution PDR rejected;
2. stale verifier head rejected;
3. frozen L5 execution context rejected inside the L6 acceptance;
4. revoked authority rejected before egress.

## Scheduling history

The first in-run Host B job (`108224114332`) was queued under the repo-scoped `aie-interop` label and was later cancelled. That is retained as execution-history evidence.

The canonical Host B proof instead consumed the exact immutable Host A artifact through Runtime's existing trusted generic Linux pool. It landed on `vps-ci-01 / vps-70333b3c`, and the orchestrator independently proved that this physical host differed from Host A before accepting the L6 claim.

No carrier-repository workaround is part of the successful evidence path.

## Claim boundary

L6 demonstrates this pinned cross-host conformance path. It does **not** prove:

- arbitrary distributed exactly-once execution;
- arbitrary shared-database failover;
- crash safety inside the indeterminate external-effect window;
- performance improvement;
- production readiness;
- independent external reproduction;
- uniqueness, world-first status or industry superiority.

The receipt retains:

- `performance_claim=false`
- `g15_9_authorized=false`
- `production_deployment=false`

## Next frontier — L7 Indeterminate Effect Reconciliation

L6 still hands off **after** the remote effect is visible and after the successful effect completion is represented in the durable TG audit chain.

The unresolved frontier originally identified after L5 remains the harder uncertainty window:

> The external effect may already have committed, but the local completion receipt is not yet durable.

L7 must inject failure inside that window and require recovery to inspect exact remote state **before any retry**.

Minimum L7 gates:

1. external commit can occur while local completion receipt is deliberately absent;
2. recovery begins with effect state = `INDETERMINATE`, never assumed absent;
3. Host B reconciles exact remote state before action retry is possible;
4. committed remote state is adopted into the original causal identity without executing the effect again;
5. absent remote state may permit a bounded retry only after reconciliation proves absence;
6. divergent/stale remote state fails closed rather than self-certifying success;
7. fencing prevents Host A and Host B from concurrently owning the same effect attempt;
8. MissionAcceptance remains impossible until exact-subject independent verification;
9. the experiment remains conformance-only and does not authorize G15-9.
