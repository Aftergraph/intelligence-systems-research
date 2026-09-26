# Changelog

## 2.14.0 — Adaptive heterogeneous swarm

- Adds verified-outcome competence learning with bounded updates and evidence de-duplication.
- Adds adaptive competence routing that preserves capability and minimum-competence gates.
- Adds hash-chained cross-provider subagent receipts with explicit non-elevation of evidence class.
- Adds adaptive topology rewriting between bounded parallel and hierarchical execution based only on verified outcomes.
- Keeps live-provider and performance claims fail-closed.

## 2.13.0 — Heterogeneous governed subagents
- Added immutable backend identities and registry-backed execution.
- Added competence-aware deterministic backend routing and capability gates.
- Added dynamic topology selector for hierarchical vs bounded-parallel execution.
- Added signed per-agent execution receipts with trace/span and provider-lineage binding.
- Added fail-closed live-provider evidence semantics separating signed from live/authenticated evidence.


## 2.12.0 — Governed multi-agent runtime

- Added hierarchical orchestrator with bounded parallel fan-out/fan-in.
- Added least-privilege context/tool scopes for subagents.
- Added dependency-output contracts, retries, fallback agents, circuit breakers, soft deadlines and evaluator fail-closed semantics.
- Added ALL/ANY/QUORUM/BEST_N join policies with terminal-only join scoping.
- Added shared trace_id / per-subagent span_id audit events and deterministic state hashes.
- Added multi-agent plan/run schemas and claim-safe `v212-demo`.
- Added 39 dedicated v2.12 tests; full suite is 329/329 PASS across six isolated shards.
- No live provider campaign was executed; historical 11.86x remains modeled, not measured.
## 2.12.0 — 2026-09-25

- Makes benchmark preflight evidence relocatable by preserving manifest-relative config/case paths instead of build-container absolute paths.
- Adds a release relocatability gate covering version drift, stale absolute evidence paths, and mutable GitHub Actions references.
- Pins remaining official GitHub Actions references to immutable commit SHAs.
- Corrects README release identity to v2.12.0.
- No live provider campaign executed in the build container; performance claims remain unchanged.

## 2.10.0 — 2026-09-25

- Connects the real fresh-worktree coding benchmark to v2.9 signed live evidence.
- Captures provider-issued response/request IDs for every model turn without logging credentials.
- Binds complete provider request lineage into receipt v2 and fails closed on missing/tampered lineage.
- Adds `live-campaign-v210` and offline `verify-live-v210` commands plus an Aftergraph self-hosted workflow.
- Live execution remains unperformed in this build container because provider credentials are absent.

# Changelog

## 2.14.0 — Adaptive heterogeneous swarm

- Adds verified-outcome competence learning with bounded updates and evidence de-duplication.
- Adds adaptive competence routing that preserves capability and minimum-competence gates.
- Adds hash-chained cross-provider subagent receipts with explicit non-elevation of evidence class.
- Adds adaptive topology rewriting between bounded parallel and hierarchical execution based only on verified outcomes.
- Keeps live-provider and performance claims fail-closed.

## 2.9.0 — 2026-09-25

### Added
- `AuthenticatedLiveHoldoutRunner` for paired provider execution with public-key evidence receipts;
- `ProviderExecutionAttestation` with provider/model/request identity, transport security, authentication state and evidence origin;
- Ed25519 sealing for every paired execution observation;
- bundle verification that recomputes the campaign digest and binds receipt identity, payload digest, execution order, status and metrics digest back to execution records;
- fail-closed `evaluate_verified` path that refuses non-live or invalidly signed evidence;
- packaged `live-provider-evidence/v1` schema, `v29-demo`, and Aftergraph self-hosted v2.9 verification workflow.

### Corrected truth boundary
- legacy `live-campaign` and `live-campaign-v25` no longer self-certify `live_provider_measurement=true` merely because provider-backed execution occurred; they now expose `provider_execution_performed=true` but remain unauthenticated under the v2.9 evidence definition.
- signed synthetic/replay evidence cannot become live measurement evidence.
- no authenticated live-provider A/B campaign or measured 10× result is claimed by this release.

## 2.8.0 — 2026-09-25

### Added
- provider-agnostic `PairedHoldoutCampaignRunner` for identical incumbent/candidate mission pairs;
- deterministic counterbalanced execution order to reduce systematic first/second-condition bias;
- immutable payload SHA-256 binding across both sides of every pair;
- phase blinding at the condition callback boundary so shadow/experiment/holdout labels are not exposed to the executed condition;
- strict, fail-closed telemetry validation before a record can enter evidence evaluation;
- direct composition with the v2.5 holdout-only promotion gate;
- `v28-demo` and packaged `paired-holdout-execution/v1` schema.

### Truth boundary
- The runner produces paired execution evidence but has **no promotion authority** and no execution-authority side effect.
- The bundled demo is synthetic. No authenticated live-provider A/B result or 10× performance claim is made.

## 2.6.0 — 2026-09-25

### Added
- whole-system `FrontierWorkloadProfile` with mutually-exclusive frontier-token accounting categories;
- evidence-gated `EfficiencyLever` model and bounded `SystemEfficiencyCompiler`;
- multiplicative overlap handling for token reductions and conservative union-bound quality retention;
- attainable-region analysis that separates observed/benchmarked mechanisms from modeled hypotheses;
- `AdaptiveContextBudgeter` for minimum-token context projections at a requested utility-retention floor;
- fail-closed `EarlyExitGate` for verified cheap-path no-frontier decisions;
- sequential `RetryBudgetOptimizer` based on marginal VSR gain per 1,000 frontier tokens;
- `efficiency-plan-v26` and `v26-demo`;
- packaged `FrontierWorkloadProfile/v1` and `SystemEfficiencyPlan/v1` schemas;
- v2.6 example workload/lever configs and Aftergraph self-hosted verification workflow.

### Truth boundary
- Compiler projections are planning hypotheses, not measured performance claims.
- Modeled 10× attainability does not imply observed 10× performance.
- Promotion remains governed by v2.5 paired holdout evidence.

## 2.5.0 — 2026-09-25

### Added
- evidence-grade paired campaign evaluator with immutable shadow/experiment/holdout allocation;
- holdout-only promotion gate with paired bootstrap VSR-delta interval;
- generator/control-plane token and cost decomposition;
- control-plane token/cost tax and frontier-control tax;
- 10× frontier-efficiency feasibility bound that detects targets impossible from control-plane offload alone;
- conservative non-inferiority sample-size planner;
- SHA-256 campaign evidence bundle and verifier;
- continuous post-promotion regression monitor with quarantine signal;
- `campaign-plan-v25`, `campaign-report-v25`, `live-campaign-v25`, `campaign-verify-v25`, and `v25-demo`;
- packaged `EvidenceCampaignReport/v1` and `CampaignEvidenceBundle/v1` schemas.

### Truth boundary
- No live provider performance claim is made by the bundled v2.5 demo.
- The paired bootstrap interval is empirical and the sample-size planner is a conservative approximation.
- Campaign bundle hashes provide integrity, not independent attestation or third-party timestamping.

## 2.4.0 — Resilient physical pair + live campaign frontier

- Added crash-durable monotonic relay session generations across relay-hub restarts.
- Added durable resumable journal checkpoints with sequence/hash-chain/terminal-head validation.
- Added a secret-free two-node physical-pair manifest and configuration doctor for Jonas-Lenovo/VDS deployment readiness.
- Added explicit token-price accounting and paired benchmark → statistical learning-campaign conversion.
- Added `live-campaign`, `physical-pair-template`, `physical-pair-doctor`, and `v24-demo` CLI paths.
- Added `physical-pair-manifest/v1` and `journal-checkpoint/v1` schemas.
- Fixed a pre-existing missing `base64` import in relay client config validation exposed by the new physical-pair doctor.
- No physical cross-host or fresh authenticated TypeSafe/Dialagram result is claimed by this release.

## 2.3.0 — Outbound relay physical-node frontier

- Added `RelayHubServer`, `RelayNodeAgent`, and `RelayCoordinatorClient` for outbound-only worker connectivity through a real mTLS TCP relay.
- Added relay session-generation fencing: a newer registration for the same node closes the older stream.
- Added end-to-end application sender→Ed25519 signing-key binding for relay paths where the original coordinator TLS certificate is not present on the worker hop.
- Added bounded remote `lease_issue`, disabled by default, with explicit issuer allowlist, capability allowlist, maximum TTL, and node-assigned monotonic fencing.
- Hardened `verify_candidate` so the fenced lease must explicitly grant the capability.
- Hardened deployable-node journal polling with lease ownership, fencing-token, capability, and stream/lease binding.
- Made receipt-carried and streamed execution journals hash-identical by streaming exact already-minted `ExecutionEvent` objects instead of timestamped copies.
- Added deployable relay hub/node/client configs, JSON Schema contracts, systemd/PowerShell templates, CLI templates, probe/serve commands, and `v23-demo`.
- Added manual Aftergraph self-hosted CI workflow for the v2.3 relay vertical.
- Physical Jonas-Lenovo↔VDS execution is still not claimed because the available remote connector was quota-blocked during this build; v2.3 implements the outbound-relay solution to remove the inbound-reachability dependency.

## 2.2.0 — Deployable physical-node boundary

- Added persistent Ed25519 node signing keys with safe load/write helpers.
- Added file-configured `NodeAgent` daemon with mTLS, bounded capabilities, durable lease fencing, fixed verifier argv and journal streaming.
- Added authenticated `NodeClientSession` and physical-node `node-probe`.
- Added `node-keygen`, `node-template`, `node-client-template`, `node-doctor`, `node-serve`, and `v22-demo` CLI paths.
- Added deploy templates for Linux systemd and Windows PowerShell.
- Added `node-agent-config/v1` and `node-client-config/v1` schemas.
- No provider or node secrets are embedded in release artifacts.

## 2.0.0 — 2026-09-25

### Added
- real loopback TCP node gateway with signed `NodeRequest` / `NodeResponse` transport.
- mutual-TLS server/client helpers and TLS peer-CN → signed-sender identity binding.
- server-side bounded `OperationRegistry`; the remote caller cannot supply arbitrary shell commands.
- durable remote lease heartbeat/renewal operations with sender and fencing-token checks.
- hash-chained `ExecutionJournal` for trajectory-integrity evidence.
- Ed25519-signed `ProofDelta` replication layered over ProofGraph revision CAS.
- verifier trust-domain diversity quorum.
- packaged `ExecutionEvent/v1` and `SignedProofDelta/v1` JSON Schema contracts.
- `jev-one v2-demo`, which executes real TCP + mTLS on loopback and composes heartbeat, remote verification, journal verification, signed proof replication and diverse quorum.

### Security / truth boundary
- the bundled PKI helper is local/reference only; production CA/SPIFFE/OIDC integration is not claimed.
- real localhost network execution is proven; Jonas-Lenovo/VDS deployment remains unexecuted from this build environment.
- TypeSafe and Dialagram provider smoke was retried with runtime-only credentials but DNS resolution failed before authentication; no live-provider-success claim is made.

## 1.9.0 — 2026-09-25

### Added
- Ed25519-signed `NodeRequest/v1` / `NodeResponse/v1` application protocol.
- HTTPS node transport with plaintext HTTP restricted to loopback.
- bounded `RemoteWorkerClient` and fenced `RemoteWorkOrder/v1` / `RemoteWorkReceipt/v1`.
- replay-nonce protection at the reference node endpoint.
- revision-fenced `ProofDelta` replication for synchronized evidence state.
- `jev-one transport-demo` and an Aftergraph self-hosted v1.9 verification workflow.

### Security / truth boundary
- no arbitrary shell operation is exposed by the remote worker protocol.
- receipt bindings are checked against mission node, lease, fencing token, candidate SHA, and work-order hash.
- a live Lenovo/VDS listener is not claimed; bundled transport verification is local/zero-network except for the mocked HTTP serialization seam.

## 1.8.0 — 2026-09-25

- Adds `WorksExecutionContext` as the explicit mission/node/principal/trace binding for networked work dispatch.
- Adds Ed25519 workload assertions with audience, execution-context, issue/expiry and nonce binding; verification requires only the registered public key.
- Adds `TrustGatewayValidator`, a fail-closed local admission contract that binds workload identity, WORKS context and an active `AuthorityGrant` before dispatch.
- Adds crash-durable `SqliteLeaseStore` with transactional monotonic fencing across process restarts, plus `WorkerDirectory` capability/health discovery and Aftergraph-native endpoint identifiers.
- Adds `SqliteProofGraphStore` with optimistic compare-and-swap revisions so stale distributed proof writers cannot silently overwrite newer evidence state.
- Adds independent-verifier quorum evaluation with unique verifier principals and conflict rejection.
- Adds Ed25519 public-key receipts alongside the existing HMAC shared-secret receipts.
- Adds provider closed/open/half-open circuit breakers integrated with explicit failover routing.
- Adds `NetworkedMissionRuntime` and `jev-one networked-demo` to compose identity, authority, durable leases, synchronized proof and quorum-gated commit in one zero-network reference vertical.
- Adds five packaged v1.8 JSON Schema Draft 2020-12 contracts and a manual Aftergraph self-hosted CI workflow for the v1.8 kernel.
- Does not claim a production network transport, distributed consensus, SPIFFE/OIDC conformance, or live TypeSafe/Dialagram A/B result.

## 1.7.0 — 2026-09-25

- Adds `AuthorityLedger` with purpose-bound scope/budget/expiry/delegation-depth attenuation, conservative delegated-budget reservation, delegation-chain hashing, and cascading revocation.
- Adds `WorkerLease` / `LeaseManager` with heartbeats, expiry, one-current-lease-per-node semantics, monotonic fencing tokens, and stale-worker rejection after reassignment.
- Adds `DistributedMissionRuntime` for bounded parallel MissionGraph execution, speculative branches, capability admission, authority checks, and lease-fenced verify/commit/fail transitions.
- Adds `ProviderFailoverRouter` with same-logical-model failover by default, retry-class gating, fail-closed authentication behavior, and explicit-only cross-model substitution.
- Adds HMAC-SHA256 `SignedReceipt` support using runtime-supplied key material; shared-secret authenticity is not represented as public-key or independent attestation.
- Adds `AutoCampaignController` for deterministic shadow → experiment → holdout phase progression without bypassing statistical promotion gates.
- Adds four packaged v1.7 JSON Schema Draft 2020-12 contracts and an offline `distributed-demo` vertical slice.
- Re-runs the authenticated provider smoke with runtime-only credentials; the build environment still fails at DNS resolution before provider authentication, and no live-provider-success claim is made.

## 1.6.0 — 2026-09-25

- Adds allowlisted `SecretResolver`, owner-only local dotenv writer, redacted provider health checks, `secret-status`, and `live-smoke`.
- Adds manual-only GitHub Actions provider smoke workflow using environment secrets and a separate secret-scan workflow; real provider values are never committed or packaged.
- Adds release-time scanning for TypeSafe `apikey_...` and Dialagram `dgr_live_...` secret shapes.
- Adds `LearningCampaign` with Wilson confidence intervals, paired VSR/CPVO/FCR gates, minimum holdout evidence, post-promotion monitoring and automatic quarantine semantics.
- Extends `PromotionRegistry` with persistent quarantine records and removal of regressing routes from active selection.
- Adds `HttpJsonEffectTransaction` with HTTPS-only host allowlisting, explicit authority, external readback, exact proof binding, and explicit-only compensation.
- Adds `MissionGraph` states and proof-aware speculative scheduling with transitive invalidation on upstream failure.
- Adds three packaged v1.6 JSON Schemas for HTTP effect receipts, learning campaigns and mission nodes.
- Fresh build-container live provider smoke reached the network boundary but DNS resolution was unavailable; no authenticated-provider-success claim is made.

## 1.5.0 — 2026-09-25

- Wires a `ShadowDecisionEngine` into the real agent decision loop; the candidate receives identical typed decision inputs but has no execution authority before evidence-gated promotion.
- Records path equivalence and exposes candidate outcomes only when the counterfactual is actually observable; divergent candidate outcomes remain unknown.
- Adds persistent `PromotionRegistry` and decision-family route activation after `LearningRatchet` + `PromotionPolicy`; promoted route failures fail closed instead of silently falling back.
- Shares the promotion registry with the Intelligence Fabric while preserving capability, predicted-VSR, authority and frontier-budget admission gates.
- Adds `FileEffectTransaction` with PREPARE/AUTHORIZE/SPECULATE/EXECUTE/READBACK/VERIFY/COMMIT/COMPENSATE states, exact pre/post hashes, proof binding and drift-safe compensation.
- Changes completion gating to fail closed when `evidence_fresh` is absent rather than defaulting freshness to true.
- Adds `shadow-inspect`, `promotion-inspect` and `effect-demo` CLI surfaces plus a Hermes Dialagram-Qwen + TypeSafe-Jev shadow profile.
- Adds four packaged v1.5 JSON Schema Draft 2020-12 contracts for action proposals, effect receipts, shadow mission summaries and promotion registries.

## 1.4.0 — 2026-09-25

- Adds Decision Distillation Compiler, shadow observations, observable-only counterfactual replay, and a fail-closed Learning Ratchet.
- Adds PromotionPolicy gates for VSR non-inferiority, FCR, CPVO, and minimum replay/shadow/experimental/holdout evidence.
- Adds competence-aware Intelligence Fabric outcomes and optional persistent competence-graph updates from governed agent missions.
- Adds empirical/manual verifier-correlation calibration and correlation-discounted verification planning.
- Adds exact fresh-evidence reuse by subject, predicate, dependency set, verifier and method.
- Adds proof-gated speculative file transactions with delayed commit, preimage drift detection, and workspace confinement.
- Adds `jev-one learning-demo` plus three packaged v1.4 JSON Schemas.

## 1.3.0 — 2026-09-25

- Adds bounded Context Compiler + Semantic Garbage Collector with utility-per-token selection and explicit projection telemetry.
- Adds persistent subject-bound Proof Graph with active/stale/revoked claim states and transitive dependency invalidation.
- Adds separate mission-acceptance proof claims so verifier success and mission acceptance remain distinct.
- Adds adaptive verification portfolio planning across assurance, detection probability, cost and latency constraints.
- Adds `$PRIMARY_VERIFY` indirection for operator-supplied verifier commands inside verification portfolios.
- Adds `verification-plan` and `proof-inspect` CLI surfaces.
- Adds packaged `ContextProjection/v1`, `EvidenceClaim/v1`, and `VerificationPlan/v1` JSON Schemas.
- Persists CLI proof state at `.jev-one/proof-graph.json` and exposes proof telemetry in mission metrics.

## 1.2.0 — 2026-09-24

- Adds the first executable Verified Intelligence Fabric slice: `DecisionRequest`, `IntelligenceBid`, `IntelligenceFabric`, `FrontierTokenBudget`, and `CompetenceGraph`.
- Adds minimum-sufficient scheduling across a common bid contract with capability, authority, predicted-VSR, frontier-budget, cost, latency, uncertainty, and risk gates.
- Adds persistent multi-dimensional competence observations using Beta posteriors without silently transferring evidence across task/environment keys.
- Adds optional generation-model selection through the Intelligence Fabric; legacy decision-backed model choice remains the compatibility path when the fabric is disabled.
- Adds `jev-one intelligence-plan` for zero-network scheduler inspection.
- Adds four versioned JSON Schema Draft 2020-12 contracts and packages them in the wheel.
- Adds an offline `rule → Jev → frontier` routing demonstration with explicitly illustrative, non-measured priors.
- Adds frontier budget telemetry to mission results when fabric routing is enabled.

## 1.1.0 — 2026-09-24

- Adds a paired Hermes control-plane ablation that holds `qwen-3.8-max-thinking` constant as the frontier generator while comparing Qwen-driven typed control against TypeSafe Jev control.
- Adds a fail-closed OpenAI-compatible `Choice` / `Score` / `Noul` decision backend for Dialagram/Nexum `/chat/completions`.
- Adds normalized provider token/cached-token telemetry, typed decision token/latency telemetry, verifier latency, completion-claim counts, false-completion counts, and per-mission control-plane token tax.
- Adds benchmark aggregation for VSR, FCR, token totals, p50 latency, turns, and control-plane tax.
- Adds five deterministic broken SWE fixtures and enforces baseline-fails + identical-generator invariants before live execution.
- Adds secret-safe Hermes `.env` loading for `DIALAGRAM_API_KEY`, `HERMES_CUSTOM_DIALAGRAM_ME_API_KEY`/`NEXUM_API_KEY`, and `TYPESAFE_API_KEY`; values are never returned.
- Adds `benchmark-preflight`, `benchmark`, and `benchmark-report` CLI commands.
- Live execution remains fail-closed when the required provider credentials are unavailable.

## 1.0.0 — 2026-09-24

- Adds a Hermes-oriented TypeSafe Jev + Dialagram/Nexum profile with the current 18-model router catalog; Qwen 3.8 Max and its thinking variant are the only entries promoted to frontier by default.
- Adds Dialagram/Nexum base-URL and credential conventions to the generic OpenAI-compatible provider factory.
- Adds an OpenAI Responses typed-decision backend so `gpt-5.6-sol` can drive Choice/Score/Noul and frontier coding with one `OPENAI_API_KEY`.
- Makes the shipped production example a single-provider GPT-5.6 Sol profile while retaining TypeSafe Jev as an optional decision backend.
- Implements the five Jev coding-loop decisions: scope, model choice, action safety, completion/judgeability, and tool-output retention.
- Enforces frontier-only coding eligibility with fail-closed `unclassified` catalog imports.
- Adds native OpenAI Responses, Anthropic Messages, Google generateContent and generic OpenAI-compatible transports.
- Adds an optional LiteLLM bridge and data-driven LiteLLM catalog import for broad provider/model coverage.
- Adds deterministic repository confinement, catastrophic command blocking, consequence approval gates, subprocess secret stripping, and redacted audit events.
- Makes fresh verifier evidence a required state transition before `VERIFIED`.
- Adds typed context compaction that restarts provider sessions after retention decisions.
- Includes zero-network end-to-end proof and HTTP contract tests using mock transports.

## 2.1.0 — Multi-Node Verified Fabric

- Added `FencedPreconfiguredVerifierCapability`: remote verifier execution now requires a live durable lease, matching fencing token, node and authority grant before the worker-owned command can run.
- Added bounded read-only streamed execution journals (`JournalStreamRegistry`, `JournalStreamService`) with cursor continuity and hash-chain head verification.
- Added `MultiNodeVerificationCoordinator` for identical-candidate verification across independent worker trust domains with diverse quorum evidence.
- Added mission measurement primitives for VSR, FCR, CPVO, mean TVO and Frontier Intelligence Efficiency.
- Added `jev-one v21-demo`: two real loopback TCP+mTLS node gateways, lease renewal over the signed node protocol, two real fixed verifier subprocesses, streamed journals and proof quorum.
- Added Aftergraph self-hosted v2.1 verification workflow and packaged schemas for journal pages and mission measurements.
- Truth boundary: the bundled demo is two network node gateways on one host; physical Jonas-Lenovo ↔ VDS execution and live TypeSafe/Dialagram A/B remain unverified.

## 2.7.0
- Added EmpiricalEfficiencyExecutionEngine: context budget -> verified cheap path -> frontier escalation -> marginal retry gate.
- Added measured per-mission frontier calls/tokens/cost receipt and `efficiency-execution-receipt/v1` schema.
- Added fail-closed frontier token budget enforcement and verifier-backed early exit.
- Added `v27-demo`; synthetic demo is explicitly not a live provider performance claim.