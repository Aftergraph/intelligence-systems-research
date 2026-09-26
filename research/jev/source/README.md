# Aftergraph Jev Engineering v2.15.0




## v2.9 authenticated live A/B evidence gate

Command: `jev-one v29-demo`. v2.9 adds Ed25519-sealed paired-provider execution receipts and a fail-closed evidence gate. A signed receipt is **not** enough to become live evidence: every execution must also declare authenticated `evidence_origin=live-provider`. The bundled demo is synthetic, so `live_provider_measurement=false` and `authenticated_live_ab_executed=false`. See `docs/V29_AUTHENTICATED_LIVE_AB_EVIDENCE.md`.

## v2.8 — paired provider holdout execution

v2.8 closes the gap between the v2.7 per-mission empirical executor and the existing v2.5 evidence-grade promotion gate. It runs the **same preregistered mission payload** through incumbent and candidate conditions, counterbalances condition order deterministically, validates telemetry fail-closed, and sends the completed paired records into the reserved holdout evaluator.

```text
preregistered mission pair
        ↓ same payload SHA-256
incumbent ⇄ candidate (counterbalanced order)
        ↓ strict telemetry contract
paired campaign execution
        ↓
shadow / experiment / HOLDOUT
        ↓
v2.5 holdout-only evaluator
        ↓
PROMOTE or REJECT (evaluation only; no authority mutation)
```

Command: `jev-one v28-demo`. The bundled demo uses deterministic synthetic adapters; `live_provider_measurement=false`. A live efficiency claim still requires authenticated provider execution over a sufficiently powered paired holdout campaign. See `docs/V28_PAIRED_PROVIDER_HOLDOUT.md`.

## v2.6: whole-system 10× efficiency compiler

v2.6 turns the 10× target into a bounded systems optimization problem instead of assuming that Jev control-plane offload is enough. It introduces mutually-exclusive frontier-token accounting categories, evidence-gated optimization levers, conservative quality-retention bounds, adaptive context budgeting, verified early exit, and marginal-value retry budgeting.

```text
measured workload profile
        ↓
context / control / retry / escalation levers
        ↓
evidence + quality gates
        ↓
attainable-region search
        ↓
SystemEfficiencyPlan
        ↓
paired implementation campaign
        ↓
OBSERVED result or REJECT
```

New commands:

```text
jev-one efficiency-plan-v26
jev-one v26-demo
```

The compiler output is explicitly **not** a 10× performance claim. The bundled synthetic demo can show a modeled region above 10× while the observed-evidence region remains below 10×. Only a paired holdout campaign may convert the hypothesis into measured evidence. See `docs/V26_SYSTEM_EFFICIENCY_COMPILER.md`.


## v2.5: evidence-grade 10× frontier-efficiency gate

v2.5 separates control-plane savings from system-level frontier efficiency. Promotion is now evaluated from a **reserved holdout slice only**; shadow and experiment observations cannot make a candidate pass holdout. Reports decompose generator/control tokens and cost, compute paired VSR deltas, expose control-plane tax, seal campaign evidence with SHA-256, and explicitly test whether a requested 10× target is even attainable by removing frontier control tokens alone.

```text
shadow → experiment → HOLDOUT ONLY → promote/reject
                              ↓
                    VSR/FCR/CPVO/FIE
                              ↓
                  10× feasibility bound
```

New commands:

```text
jev-one campaign-plan-v25
jev-one campaign-report-v25
jev-one live-campaign-v25
jev-one campaign-verify-v25
jev-one v25-demo
```

A 10× target is a research target, not a release claim. If the same frontier generator dominates token use, the report can prove that control-plane offload alone cannot reach 10× and quantify the additional generator/context reduction required. See `docs/V25_EVIDENCE_GRADE_10X_GATE.md`.

## v2.4: resilient physical pair + live intelligence campaign

v2.4 makes the outbound relay restart-resilient and connects paired provider evidence to the statistical promotion gate. New primitives persist relay session generations, resume hash-chained journal polling after reconnects, validate a two-node Jonas-Lenovo/VDS deployment manifest, and run a real paired benchmark into shadow → experiment → holdout promotion using explicit operator-supplied pricing.

Key commands:

```text
jev-one physical-pair-template
jev-one physical-pair-doctor physical-pair.json
jev-one live-campaign benchmarks/hermes_qwen_control_plane_ablation.yaml --pricing pricing.json --incumbent qwen-frontier-control --candidate qwen-jev-control
jev-one v24-demo
```

`live-campaign` uses runtime credentials and does not embed provider secrets. Prices are not baked in as claims. Physical pair readiness and live provider execution remain separate evidence states. See `docs/V24_RESILIENT_PHYSICAL_PAIR_AND_LIVE_CAMPAIGN.md`.

## v2.3: outbound-only physical node relay

v2.3 solves the primary v2.2 physical-network wall: workers no longer need a directly reachable inbound listener. `RelayNodeAgent` establishes an mTLS connection **outbound** to a reachable relay hub, while the original `NodeRequest`/`NodeResponse` remain end-to-end Ed25519 signed and are still verified by the bounded worker `NodeGateway`.

```text
Coordinator --mTLS--> Relay Hub <--outbound mTLS-- Worker
     |                                      |
     +------ signed NodeRequest ------------+
                                            ↓
                                   bounded capabilities
                                   + fenced remote lease
                                   + fixed verifier
                                   + proof journal
```

New CLI paths:

```bash
jev-one relay-hub-template -o relay-hub.json
jev-one relay-node-template -o relay-node.json --node-config-file node.json
jev-one relay-client-template -o relay-client.json --sender-id coordinator --worker-id worker:jonas-lenovo
jev-one relay-hub-serve relay-hub.json
jev-one relay-node-serve relay-node.json
jev-one relay-probe relay-client.json
jev-one v23-demo
```

Remote lease issuance is disabled unless an issuer is explicitly allowlisted and bound to an application signing key. Lease capabilities are node-policy-bounded, `verify_candidate` checks the capability on the current fenced lease, and strict journal polling requires the same live lease. Duplicate node registrations increment a relay session generation and close the old session.

The v2.3 reference demo runs the complete outbound-relay path on one host over real TCP+mTLS. Physical Jonas-Lenovo ↔ VDS execution remains a deployment step; this release does not fabricate that evidence. See `docs/V23_OUTBOUND_RELAY_FABRIC.md`.


## v2.0: real mTLS node fabric

v2.0 executes the signed Aftergraph node protocol over a real TCP socket on loopback with mutual TLS, application-layer Ed25519 signatures, TLS peer-to-sender binding, durable lease heartbeats, hash-chained execution journals, signed proof replication and verifier trust-domain diversity.

```bash
jev-one v2-demo
```

This is a real network transport proof, not a physical multi-machine deployment claim. The bundled certificate authority exists for reference/local execution; use managed workload identity in production. See `docs/V20_NETWORKED_FABRIC.md`.


A production-oriented reference harness for the **Jev Engineering** coding loop: frontier models perform generative work while typed control decisions, evidence, effect transactions, bounded learning and mission-graph semantics govern how that intelligence is spent. Production profiles include TypeSafe Jev System One and Dialagram/Nexum Qwen routes without embedding provider credentials in source or release artifacts.

The central invariant is deliberately strict:

> **The coding model can propose work and completion. It cannot authorize itself and it cannot mint `VERIFIED`.**

`jev-one` always filters the coding route to models explicitly classified as `tier: frontier`. Discovered/catalog models default to `unclassified` and are invisible to the coding router until an operator explicitly promotes them.

## v1.9 signed node transport

v1.9 adds an authenticated transport layer between the v1.8 identity/lease/proof contracts and future Aftergraph compute nodes. Ed25519-signed node messages carry bounded JSON operations; remote work receipts are bound to the exact execution context, lease, fencing token, authority grant and candidate SHA. Proof deltas use optimistic revision fencing so stale replicas cannot overwrite newer evidence.

Quick local proof:

```bash
jev-one transport-demo
```

See `docs/V19_NODE_TRANSPORT.md`. A real Jonas-Lenovo/VDS listener is a deployment step beyond this release and is not represented as completed evidence.

## v1.8: Networked Verified Intelligence Fabric

v1.8 binds the distributed kernel to explicit WORKS execution context, public-key workload identity, Trust Gateway-style admission, crash-durable lease fencing, synchronized proof revisions, independent-verifier quorum, provider circuit breakers and public-key receipts.

```text
WORKS ExecutionContext
      ↓
Ed25519 workload assertion
      ↓
TrustGatewayValidator
 identity + authority
      ↓
WorkerDirectory
      ↓
SqliteLeaseStore / fencing
      ↓
MissionGraph work
      ↓
SqliteProofGraphStore / CAS revision
      ↓
independent verifier quorum
      ↓
COMMIT
      ↓
Ed25519 public receipt
```

Run the zero-network reference vertical:

```bash
jev-one networked-demo
```

The demo proves the local contracts compose. It deliberately reports `network_transport_executed: false`: `aftergraph://...` worker addresses are identifiers in this release, not a live remote transport. SQLite is the crash-durable reference backend rather than a distributed consensus database, and the workload assertion is Aftergraph-native Ed25519 rather than a claim of SPIFFE/OIDC conformance. See `docs/NETWORKED_FABRIC.md`.


## v1.7: Distributed Verified Intelligence Fabric

`v1.7.0` adds the first distributed-execution kernel around the existing mission, proof, effect, and learning planes. The design remains fail-closed: a worker assignment is not authority, a lease is not proof, provider failover is not permission to change logical models, and a signed receipt is not the same thing as independent verification.

### Federated authority attenuation

`AuthorityLedger` issues purpose-bound grants and child delegations with deterministic attenuation across scope, budget, expiry, and delegation depth. Child scopes must be subsets of parent scopes, child expiry cannot exceed parent expiry, delegated budget is conservatively reserved, and revocation cascades to descendants.

```text
human authority
      ↓
root grant
      ↓  attenuate only
worker/team grant
      ↓
mission/effect authorization
```

### Lease-fenced distributed workers

`LeaseManager` and `DistributedMissionRuntime` add one-current-lease-per-node execution with monotonically increasing fencing tokens, heartbeats, expiry, reassignment fencing, capability checks, authority checks, bounded parallelism, and MissionGraph integration. A stale worker cannot verify or commit after a newer worker has been assigned the same node. Independent graph branches can run concurrently while joins remain proof-gated.

### Explicit provider failover

`ProviderFailoverRouter` supports retryable provider failover while preserving the requested logical model by default. Transient/rate-limit failures may move to another route for the same logical model. Authentication failures fail closed unless an operator explicitly opts into auth failover, and cross-model substitution requires a separate explicit opt-in.

### Authenticated receipts

`ReceiptSigner` / `ReceiptVerifier` add canonical HMAC-SHA256 integrity/authenticity for effect/worker receipts using runtime-supplied key material. This is deliberately described as shared-secret receipt authentication, not public-key attestation or independent verification.

### Automatic learning campaign progression

`AutoCampaignController` can advance bounded shadow → experiment → holdout phases after configured evidence counts. It cannot fabricate counterfactual outcomes and cannot bypass the existing statistical promotion gate.

### Offline vertical demo

```bash
jev-one distributed-demo
```

The demo exercises two parallel worker branches, a speculative join, authority checks, lease fencing, same-logical-model provider failover, automatic learning-campaign promotion on synthetic samples, and signed-receipt verification. Its outcomes are synthetic implementation evidence only.

## v1.6: Secure Provider Runtime + Statistical Learning Campaigns + Network Effects + Mission Graph

`v1.6.0` hardens the provider/runtime boundary and extends the adaptive execution plane.

### Provider secrets without secret-in-code

The runtime now has one allowlisted `SecretResolver` for `TYPESAFE_API_KEY` and `DIALAGRAM_API_KEY` (plus historical Hermes Dialagram aliases). It supports process environment and explicit untracked dotenv files, returns presence/source metadata rather than values, and can emit only short SHA-256 fingerprints for correlation. A release secret scanner rejects TypeSafe- and Dialagram-shaped credentials in source/release files.

GitHub Actions wiring is included in `.github/workflows/live-provider-smoke.yml`. It is manual-only, references the `provider-smoke` environment, and receives credentials from GitHub Actions **environment secrets** named `TYPESAFE_API_KEY` and `DIALAGRAM_API_KEY`. The package never stores those values in YAML, wheels or ZIPs.

```text
GitHub encrypted environment secrets
        │
        ├─ TYPESAFE_API_KEY
        └─ DIALAGRAM_API_KEY
        │
        ▼
manual provider-smoke job
        │
        ▼
process environment
        │
        ▼
SecretResolver
        │
        ├─ TypeSafe Jev
        └─ Dialagram / Qwen
```

Inspect locally without printing values:

```bash
jev-one secret-status
jev-one secret-status --env-file .env.local --fingerprint
```

Authenticated health check:

```bash
jev-one live-smoke --env-file .env.local
```

### Statistical learning campaigns

`LearningCampaign` adds paired incumbent/candidate observations, Wilson confidence intervals, VSR non-inferiority, FCR ceilings, CPVO improvement gates, minimum holdout sample requirements, and immediate post-promotion quarantine on false completion. `PromotionRegistry` now records quarantined routes and removes them from active selection.

### Proof-gated HTTP effects

`HttpJsonEffectTransaction` extends the file-only effect model to explicitly allowlisted HTTPS JSON APIs. A mutation must be prepared and authorized, then receive an external readback, exact proof binding to the readback hash, and a commit. Compensation is never inferred: it exists only when an explicit compensation request was prepared.

### Mission graph speculation

`MissionGraph` separates `READY`, `BLOCKED`, `SPECULATING`, `VERIFIED`, `COMMITTED`, `FAILED` and `INVALIDATED`. A speculative node may compute before dependencies finish but cannot become verified/committed until all prerequisites are verified. Upstream failure transitively invalidates descendants.

The v1.6 live-provider attempt in the build environment was credentialed but blocked before authentication by DNS resolution. The failure was recorded without printing or persisting the supplied secret values; therefore this release does **not** claim fresh authenticated provider success from the build container.


## v1.5: Live Shadow Control + Evidence-Gated Route Promotion + Effect Transactions

`v1.5.0` wires the learning plane into the real coding-agent loop. A candidate decision backend can run in **shadow mode** beside the incumbent while the incumbent retains execution authority. Candidate failures and divergences are observations only until a `LearningCandidate` passes replay, shadow, experiment, holdout and the hard `PromotionPolicy`. A promoted decision-family route can then become active without bypassing deterministic tool policy, capability, quality, authority, or frontier-budget gates.

```text
incumbent decision ───────────────→ active route
        │
        └──── candidate shadow ───→ observe only
                                      │
                              verified outcome
                                      │
                     replay → shadow → experiment → holdout
                                      │
                                hard policy
                                ↙       ↘
                             reject   promote
                                          │
                                 decision-family route
```

Counterfactual outcomes remain unknown when a shadow decision would have changed the execution path. Once a candidate route is promoted, its failure is **fail-closed** rather than silently falling back to the incumbent.

The second v1.5 primitive is `FileEffectTransaction`, a reversible file-effect state machine:

```text
PREPARE → AUTHORIZE → SPECULATE → EXECUTE → READBACK → VERIFY → COMMIT
                                                           └────→ COMPENSATE
```

It binds the exact preimage, proposed postimage, principal, authority reference, readback hash and verifier claim IDs. Compensation refuses to overwrite newer workspace state. This adapter is intentionally **file-only**; deployments, IAM, billing, email and arbitrary shell/network effects are not claimed reversible.

Operational inspection:

```bash
jev-one shadow-inspect .jev-one/shadow-decisions.jsonl
jev-one promotion-inspect state/promoted-routes.json
jev-one effect-demo
```

For Hermes, `configs/hermes-dialagram-qwen-shadow-jev.yaml` keeps Qwen 3.8 Max Thinking as the active Dialagram control/generation route while Jev runs as a no-authority shadow candidate. Production promotion still requires explicit experiment/holdout evidence; this release does not fabricate those metrics.


## v1.4: Bounded Learning + Shadow Replay + Proof-Gated Speculation

`v1.4.0` adds an explicit learning ratchet around the existing decision, context and proof fabrics. Expensive frontier decisions can be nominated for distillation, evaluated in replay/shadow/experimental/holdout stages, and promoted only after policy gates pass. The package does not auto-train Jev or silently replace production routes.

```text
verified decision traces
        ↓
Decision Distillation Compiler
        ↓
LearningCandidate
        ↓
REPLAY → SHADOW → EXPERIMENT → HOLDOUT
        ↓
VSR / FCR / CPVO promotion policy
      ↙           ↘
   REJECT       PROMOTE
                   ↓
          CompetenceGraph update
```

The verification planner can consume pairwise verifier-correlation evidence. Positive correlation reduces the incremental detection credit above the strongest single verifier; with no matrix configured, v1.3's independence behavior is preserved.

Proof reuse is deliberately strict: only fresh, positive claims with the exact subject, predicate and dependency set are reusable. `SpeculativeFileTransaction` adds a file-only `compute early, commit late` primitive: staged writes are invisible to the workspace until prerequisite proof is accepted, and commit fails if a target preimage changed after staging.

Run the zero-network vertical proof with:

```bash
jev-one learning-demo
```

This release still makes no 10×/50×/100× claim. Distillation candidates, verifier probabilities and routing priors become scientific evidence only after preregistered paired benchmarks and holdout evaluation.


## v1.3: Context + Proof + Adaptive Verification

`v1.3.0` adds the second executable Verified Intelligence Fabric slice. It reduces avoidable frontier context, turns verification output into subject-bound evidence, persists a proof graph that becomes stale when its dependencies change, and can select a bounded verification portfolio from assurance/detection/cost constraints.

The new runtime path is:

```text
Jev scope scores
    ↓
Context Compiler + Semantic GC
    ↓
bounded frontier context
    ↓
frontier coding + governed tools
    ↓
adaptive Verification Portfolio
    ↓
EvidenceClaim(subject SHA + dependencies)
    ↓
ProofGraph
    ↓
typed done/judgeable gate
    ↓
MissionAcceptance claim
    ↓
VERIFIED
```

Key boundaries:

- **ContextProjection is planning evidence, not billing telemetry.** Token estimates are provider-neutral approximations.
- **Fresh evidence may still have a failing verdict.** Freshness and correctness are separate dimensions.
- **A changed dependency invalidates downstream claims transitively.** Persisted proof is not silently reused after workspace drift.
- **Verification planning is fail-closed.** If assurance, detection probability, or cost constraints cannot be met, there is no admissible plan.
- **Verifier portfolios use an explicit independence approximation** for combined defect-detection probability until measured correlation data exists.

Zero-network planning:

```bash
jev-one verification-plan -c configs/verified-intelligence-v13-demo.yaml
```

A coding run with a configured proof graph writes `.jev-one/proof-graph.json`; inspect it with:

```bash
jev-one proof-inspect .jev-one/proof-graph.json
```

The bundled `context_compiler` uses Jev scope scores as semantic relevance, removes exact duplicate/stale/invalidated chunks, ranks by utility-per-token, and enforces a hard token budget before the frontier provider session is created.

## v1.2: Verified Intelligence Fabric — first vertical slice

`v1.2.0` adds the first executable slice of the STEWARD minimum-sufficient-intelligence architecture. The coding harness can now route a typed `DecisionRequest` through one common `IntelligenceBid` contract spanning deterministic rules, Jev/System-1, and frontier intelligence. Selection is fail-closed on required VSR, authority, capability, and a mission-scoped frontier-token budget.

The new slice includes:

- **Decision Fabric:** one request/bid contract instead of hard-wiring every cognitive decision to a frontier LLM;
- **IntelligenceBid:** predicted verified-success probability, estimated cost/latency, uncertainty, risk, capabilities, and frontier-token demand;
- **FrontierTokenBudget:** explicit input/output-token admission and reservation for frontier strategies;
- **CompetenceGraph:** multi-dimensional Beta-posteriors for observed strategy success with persistent JSON round-trip;
- **generation routing integration:** an enabled fabric can select the frontier coding model before a provider session is created;
- **versioned JSON Schemas:** packaged Draft 2020-12 contracts for `DecisionRequest`, `IntelligenceBid`, `FrontierTokenBudget`, and `CompetenceObservation`.

The critical boundary remains unchanged: **cognition selects/proposes; cognition does not grant authority.** `DecisionRequest.authority_granted=false` fails closed before any bid can be selected.

Try the zero-network scheduler proof:

```bash
jev-one intelligence-plan -c configs/intelligence-fabric-demo.yaml --capability control --required-vsr 0.80
jev-one intelligence-plan -c configs/intelligence-fabric-demo.yaml --capability control --required-vsr 0.90
jev-one intelligence-plan -c configs/intelligence-fabric-demo.yaml --capability control --required-vsr 0.98
```

The bundled demo uses explicitly labelled **illustrative priors, not measured benchmark results**. It deterministically demonstrates the route `rule → Jev → frontier` as the required VSR rises. Production priors should come from preregistered benchmark evidence or persisted competence observations.

## The five Jev decisions

| Loop question | Typed decision | Runtime use |
| --- | --- | --- |
| Which files? | `Score` | Rank candidate repository chunks before the frontier model sees them. |
| Which model? | `Choice` | Choose only among policy-eligible frontier profiles. |
| Safe to run? | `Noul` × 2 | Estimate destructive/irreversible risk and human-review need after deterministic policy. |
| Done? | `Noul` × 2 | Judge **fresh verifier evidence**, never the model's self-summary. |
| Keep or drop? | `Score` | Compact long tool histories by retaining/truncating/dropping exact records. |

There is also an optional `Noul` loop detector for repeated non-progress. It is an extra runtime safeguard, not one of the five core stations.

## End-to-end control flow

```text
human task
   │
   ├─ local candidate discovery
   │       ↓
   │   Score(scope)
   │       ↓
   │   selected repository context
   │
   ├─ frontier allowlist
   │       ↓
   │   Choice(model)
   │       ↓
   │   frontier coding session
   │
   └─ tool call
           ↓
     deterministic preflight
       ├─ hard block ───────────────► BLOCKED
       ├─ consequence ─► human ─────► approve / NEEDS_HUMAN
       └─ bounded action
                 ↓
         Noul(safety)
                 ↓
              execute
                 ↓
       exact tool result/evidence
                 ↓
       Score(retention) as needed
                 └──────────────► frontier session

frontier says "done"
        ↓
fresh operator-owned verifier command
        ↓
Noul(done) + Noul(judgeable)
        ├─ insufficient/failing evidence ─► frontier continues with evidence
        └─ passed evidence gate ──────────► VERIFIED
```

## Provider/model fabric

There is no closed provider enum at the policy layer. A `ModelProfile` declares a transport and provider metadata, and a data-driven registry can contain any number of providers/models.

Typed decision backends included:

- OpenAI Responses API (`decision.backend: openai`) — using `gpt-5.6-sol`
- OpenAI-compatible chat/tool API (`decision.backend: openai_compatible`) — for gateways such as Dialagram/Nexum
- TypeSafe Jev System One (`decision.backend: jev` / `typesafe`)
- explicit local heuristic (`decision.backend: local`) for offline smoke tests only

Native coding transports included:

- OpenAI Responses API (`openai_responses`)
- Anthropic Messages API (`anthropic_messages`)
- Google `generateContent` (`google_generate_content`)
- generic OpenAI-compatible gateways (`openai_compatible`)
- LiteLLM bridge (`litellm`) for the broader provider/model ecosystem

Built-in base-URL/key conventions cover common OpenAI-compatible providers such as OpenRouter, Mistral, DeepSeek, xAI, Groq, Together, Fireworks, Cerebras and Perplexity, plus local Ollama/vLLM-compatible endpoints. Unknown providers still work when a compatible `base_url` is declared or through LiteLLM.

**"All providers/models" is implemented as an extensible catalog/transport architecture, not as a claim that every remote provider was live-called in this release.** LiteLLM catalog entries are imported dynamically and remain `unclassified` until explicitly allowlisted as frontier.

## Install

Core:

```bash
python -m pip install -e .
```

With the optional broad provider bridge:

```bash
python -m pip install -e '.[all-providers]'
```

Development:

```bash
python -m pip install -e '.[dev]'
```

## Configure

```bash
cp configs/jev-one.example.yaml jev-one.yaml
export OPENAI_API_KEY='...'
```

The default profile uses OpenAI `gpt-5.6-sol` for both typed decisions and frontier coding. Additional provider examples remain available in `configs/providers.example.yaml`; non-OpenAI entries are deliberately `unclassified` until you explicitly promote them based on current vendor documentation and your own evals.

If you prefer the original TypeSafe Jev decision plane, switch `decision.backend` to `jev` and provide `TYPESAFE_API_KEY`; the coding-model registry is unchanged.

### Hermes: TypeSafe Jev + Dialagram/Nexum

A ready-to-run Hermes-oriented profile is included at `configs/hermes-dialagram-typesafe.yaml`. It keeps the low-cost typed control plane on TypeSafe Jev while sending generative coding work to Dialagram's OpenAI-compatible router.

```bash
export TYPESAFE_API_KEY='...'
export DIALAGRAM_API_KEY='...'
jev-one doctor -c configs/hermes-dialagram-typesafe.yaml
jev-one models -c configs/hermes-dialagram-typesafe.yaml --frontier-only
```

The profile contains the current 18-model Dialagram catalog captured on 2026-09-24. Only `qwen-3.8-max-thinking` and `qwen-3.8-max` are promoted to `tier: frontier`; the remaining entries stay `unclassified` until Aftergraph's own evaluation promotes them. If an existing Hermes profile stores the Dialagram credential under a different environment-variable name, change only `api_key_env` locally rather than copying the secret into YAML or source control.

For a broad catalog:

```bash
jev-one sync-models --output configs/litellm-model-catalog.json
```

Then explicitly promote only current frontier models:

```yaml
catalog:
  path: ./configs/litellm-model-catalog.json
  frontier_models:
    - openai/gpt-5.6-sol
```

Catalog discovery is **not** permission.

## Run

Inspect configuration without network calls:

```bash
jev-one doctor -c jev-one.yaml
jev-one models -c jev-one.yaml --frontier-only
```

Run a governed coding mission:

```bash
jev-one run \
  --workspace /path/to/repo \
  --config jev-one.yaml \
  --verify 'python -m pytest -q' \
  'Fix the failing authentication regression and preserve current behavior'
```

Known consequential shell actions are never silently approved. Add `--interactive-approvals` if you want the CLI to stop and ask for explicit approval. Deterministic hard-deny actions cannot be overridden by that prompt.


## Hermes paired control-plane benchmark

`v1.1.0` adds a paired live ablation that holds the **frontier generator constant** while changing only the decision plane:

```text
Condition A: Qwen 3.8 Max Thinking → typed decisions + generation
Condition B: Jev                  → typed decisions
             Qwen 3.8 Max Thinking → generation
```

The generator-invariant is checked before execution. This means a quality difference cannot be attributed simply to switching the coding model. The benchmark records per mission:

- Verified Success Rate (VSR);
- false completion claims caught by the deterministic verifier;
- frontier and decision-plane input/output tokens;
- cached-input tokens when the provider reports them;
- wall, provider, decision and verification latency;
- control-plane token tax;
- exact redacted JSONL audit evidence.

The bundled five-case SWE smoke set is intentionally small; it validates the measurement path and supports a first paired live experiment. It is **not** sufficient to make general frontier-quality claims.

On the Windows Hermes host, credentials can be loaded without copying their values into config or logs:

```powershell
jev-one benchmark-preflight benchmarks/hermes_qwen_control_plane_ablation.yaml --hermes-profile avc
jev-one benchmark benchmarks/hermes_qwen_control_plane_ablation.yaml --hermes-profile avc --repeats 3 -o benchmark-results/hermes-qwen
```

The loader reads only `DIALAGRAM_API_KEY`, the historical Hermes alias `HERMES_CUSTOM_DIALAGRAM_ME_API_KEY`/`NEXUM_API_KEY`, and `TYPESAFE_API_KEY`. Secret values are never returned by the loader. Existing process environment variables win by default.

To aggregate an existing raw run without contacting providers:

```bash
jev-one benchmark-report benchmark-results/hermes-qwen/results.jsonl
```

## Zero-network proof

A deterministic vertical slice is included so the orchestration can be proven without pretending a mock is a live Jev/frontier call:

```bash
jev-one demo
```

Expected terminal state:

```text
mode: offline-contract-proof-not-live-jev-or-frontier-api
status: verified
verification_exit_code: 0
```

The demo exercises `Score(scope) → Choice(model) → Noul(safety) → coding tools → fresh verifier → Noul(done/judgeable)` with scripted typed answers and a scripted frontier contract simulator.

## Security and authority

The package enforces several boundaries before any probabilistic decision:

- repository path confinement; absolute paths and `..` escapes are rejected;
- deterministic hard-deny patterns for catastrophic commands;
- default `verify_only` mode rejects shell chaining/substitution/redirection and absolute/parent-path arguments;
- mandatory human approval for known consequential external mutations;
- provider/API credentials stripped from command subprocesses;
- read-only tools bypass model risk judgment but remain workspace-bound;
- unknown tools are blocked;
- no natural-language model completion can transition directly to `VERIFIED`.

For ambiguous shell actions, the typed decision backend receives a redacted semantic command rather than a content-blind hash; common token/key/password literals are stripped first. The model is still a **decision plane**, not an authorization credential. See [`SECURITY.md`](SECURITY.md).

## Verification contract

A model's final message triggers a fresh, operator-configured verification command. Verification succeeds only when:

```text
verification_exit_code == 0
AND evidence_fresh == true
AND P(done | evidence) >= 0.85
AND P(judgeable | evidence) >= 0.80
```

If the process exits zero but the typed decision backend considers the evidence ambiguous or incomplete, a new frontier session receives the exact fresh evidence and continues working. `Complete != Verified` is therefore implemented as control flow, not prose.

## Typed context compaction

Every `retention_every` turns, exact recent tool records are scored. Records may be:

- kept verbatim;
- truncated to a bounded exact prefix;
- dropped.

The provider session is restarted from selected source context plus retained records, so discarded history is actually removed instead of remaining hidden in the provider conversation.

## Audit

Default CLI runs write `.jev-one/audit.jsonl` inside the workspace. The audit records model/provider/version, decision outcomes, tool names, hashes/byte counts, verifier evidence and final state while redacting common secret fields/patterns.

It is intentionally not a signed/tamper-evident evidence store. The seam is designed to be replaced by Aftergraph Evidence/OpenTelemetry receipts in a production integration.

## Repository map

```text
src/jev_engineering/
  agent.py                  governed coding loop
  decisions.py              five typed decisions + loop guard
  jev_client.py             TypeSafe System One HTTP client
  openai_decisions.py       GPT-5.6 Sol typed Choice/Score/Noul backend
  compatible_decisions.py   OpenAI-compatible typed decision backend
  benchmark.py              paired live-ablation runner + VSR/FCR metrics
  intelligence_fabric.py    DecisionRequest/Bid scheduler, budget, competence graph
  telemetry.py              cross-provider token telemetry normalization
  schemas/                  packaged v1 decision/fabric JSON Schemas
  credentials.py            allowlisted Hermes dotenv credential loader
  model_registry.py         data-driven model/provider catalog
  config.py                 YAML + catalog composition
  tools.py                  repository tools + deterministic authority
  audit.py                  redacted append-only local audit
  providers/
    openai_responses.py
    anthropic_messages.py
    google_generate_content.py
    openai_compatible.py
    litellm_bridge.py
    factory.py
    mock.py
configs/                    examples
scripts/                    verify/demo/catalog helpers
tests/                      deterministic contract + integration tests
docs/                       architecture/research/verification
```

## Verification and limitations

Run the release gate:

```bash
./scripts/verify.sh
```

See [`docs/VERIFICATION.md`](docs/VERIFICATION.md) for the exact release commands and observed results.

This release does **not** claim an OS sandbox, kernel egress control, live-provider conformance for every vendor, or that mocked HTTP contracts prove remote production availability. Remote provider calls require outbound network access and real provider credentials. A ChatGPT subscription/session is not an API credential; autonomous `gpt-5.6-sol` execution uses `OPENAI_API_KEY`.

## License

Apache-2.0. See [`LICENSE`](LICENSE).

## v2.1 Multi-Node Verified Fabric

v2.1 extends the v2.0 networked kernel with lease-fenced remote verification, bounded hash-chained journal streaming, independent multi-node proof quorum and explicit VSR/FCR/CPVO/TVO/FIE measurement primitives.

Run the local network vertical:

```bash
jev-one v21-demo
```

The demo opens two actual loopback TCP+mTLS worker gateways, renews fenced leases through the signed protocol, executes two fixed worker-owned verifier subprocesses, polls their completed journal streams and admits the candidate only after independent trust-domain quorum. It intentionally reports `physical_multi_machine_executed=false`: physical Jonas-Lenovo/VDS execution is a separate deployment gate.

## v2.2 deployable node boundary

v2.2 adds a physical-node deployment seam around the signed Aftergraph node protocol. Use `node-keygen`, `node-template`, `node-doctor`, `node-serve`, `node-client-template`, and `node-probe` to provision and authenticate a bounded worker node. See `docs/V22_DEPLOYABLE_NODES.md`.

`node-serve` does not provide arbitrary remote shell execution. The configured verifier command is server-owned, leases are fenced, and remote HTTP requires TLS outside loopback.

## v2.7 — Empirical Efficiency Execution Engine

v2.7 moves v2.6 planning into an executable, fail-closed mission path. The engine compiles context, attempts a verifier-backed cheap path, escalates to frontier only when required, applies marginal retry economics, and emits measured frontier-token/cost telemetry. `VERIFIED` is accepted only from caller-supplied verifier evidence; model self-report is not verification.

```bash
jev-one v27-demo
```

The bundled demo is deterministic/synthetic and proves execution mechanics, not live provider efficiency. Real 10x claims still require paired holdout missions.


## v2.10 authenticated provider lineage

See `docs/V210_AUTHENTICATED_PROVIDER_LINEAGE.md`. The live path now seals real provider request lineage from the existing deterministic coding benchmark. A signed bundle is not labeled live unless every execution has authenticated HTTPS transport and provider-issued request IDs.

## v2.15 — counterfactual routing, shadow challengers, and runner-sealed provider credentials

v2.15 adds explicitly modeled counterfactual route estimates, calibration against later independently verified challenger outcomes, competence decay toward a declared prior, and topology outcome memory. Counterfactual estimates are always labeled `modeled_only=true`; they never count as measured provider evidence.

Provider credentials are installed through a runner-sealed envelope. The repository contains only RSA-OAEP ciphertext bound to the persistent Aftergraph runner public key. The private unsealing key and Ed25519 evidence-signing key remain on the self-hosted node. Secrets are decrypted into process memory only for the one-shot authenticated smoke path and are never written to source, release archives, logs, or receipts.