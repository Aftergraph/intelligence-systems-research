# Architecture

## 1. Contract

The runtime separates six planes:

```text
Intent          human task
Decision        typed Choice / Score / Noul judgments
Cognition       frontier coding model
Authority       deterministic policy + explicit approval
Execution       local bounded tools
Assurance       fresh verifier + evidence gate
```

The separation is an invariant, not just packaging. A decision model may estimate risk, but it cannot grant authority. A coding model may propose completion, but it cannot mint `VERIFIED`.

## 2. Control/data flow

```text
                       ┌──────────────────────────────┐
                       │          Human task          │
                       └──────────────┬───────────────┘
                                      │
                                      ▼
                            local candidate scan
                                      │
                            ┌─────────▼─────────┐
                            │ Score: scope     │
                            └─────────┬─────────┘
                                      │
                                      ▼
                                exact file read
                                      │
                            ┌─────────▼──────────┐
                            │ Choice: model     │
                            └─────────┬──────────┘
                                      │ only eligible frontier profiles
                                      ▼
                         ┌──────────────────────────┐
                         │ Frontier coding session │
                         └───────────┬──────────────┘
                                     │ tool call
                                     ▼
              ┌──────────────────────────────────────────────┐
              │ deterministic workspace + authority policy │
              └──────┬───────────────────┬───────────────────┘
                     │ block             │ ask              │ allow/ambiguous
                     ▼                   ▼                  ▼
                   DENY             human approval       Noul × 2
                                                            │
                                                 ┌──────────┴──────────┐
                                                 │                     │
                                               block/ask             allow
                                                 │                     │
                                                 └──────────┬──────────┘
                                                            ▼
                                                     real tool result
                                                            │
                                                  if context pressure
                                                            ▼
                                                   Score retention
                                                            │
                                                            └──────► frontier

frontier emits final text
        │
        ▼
fresh configured verification command
        │
        ▼
Noul(done) + Noul(judgeable)
        │
   ┌────┴────┐
   │         │
 fail      pass
   │         │
   ▼         ▼
exact       VERIFIED
evidence
   │
   └────────► frontier continues
```

## 3. Why the model registry is data, not code

A finite enum of providers becomes stale immediately. `ModelRegistry` therefore consumes profiles plus optional LiteLLM catalog data. Each profile carries the transport needed to invoke it:

```python
ModelProfile(
    alias="openai-astra",
    provider="openai",
    model="gpt-5.6-sol",
    tier="frontier",
    transport="openai_responses",
    api_key_env="OPENAI_API_KEY",
)
```

The decision backend sees labels/descriptions, not provider credentials. The selected alias is resolved to a transport only after eligibility filtering.

### Frontier invariant

The source registry may contain thousands of models. `frontier_required=True` filters the decision surface before the `Choice` request. The decision model literally cannot choose an entry that policy did not expose.

This is the same pattern used for tools: **discovery ≠ permission**.

## 4. Decision ABI

`DecisionEngine` depends only on:

```python
backend.system_one(state: dict, questions: dict) -> DecisionResult
```

Production backends are `OpenAIDecisionBackend` (OpenAI Responses), `OpenAICompatibleDecisionBackend` (forced tool-call decisions over OpenAI-compatible chat endpoints such as Dialagram/Nexum), and `JevClient`; tests use `ScriptedDecisionBackend`; the offline harness can use `HeuristicDecisionBackend` while explicitly labeling it non-production.

The ABI keeps orchestration tests independent of network access and provider credentials.

## 5. Provider ABI

A provider creates a session:

```python
session = provider.start(task=..., context=..., tools=..., instructions=...)
turn = session.step(tool_outputs=None)
turn = session.step({call_id: tool_result})
# Failed verifier evidence starts a fresh frontier session with exact evidence.
```

This permits:

- Responses-native models;
- OpenAI-compatible gateways;
- LiteLLM-mediated providers;
- deterministic mock providers for tests.

## 6. Verification semantics

`verify_command` is configuration owned by the operator, not by the model. The model may run tests during work, but that output is only work trajectory. When the model stops calling tools and emits a final answer, the outer loop executes `verify_command` again.

`DecisionEngine.done()` fails closed if verifier evidence is absent. It then requires:

```text
verification_exit_code == 0
AND evidence_fresh == true
AND P(done | evidence) >= threshold
AND P(judgeable | evidence) >= threshold
```

That gives two independent rejection paths: the deterministic verifier can fail, or the evidence can be insufficient/ambiguous even when the process exits zero.

## 7. Security model

### Absolute boundaries

Deterministic controls run before Jev:

- workspace confinement;
- catastrophic command blocklist;
- single-command/no-shell-chaining enforcement in default `verify_only` mode;
- mandatory human approval for known consequential external mutations;
- no provider/API credentials in subprocess environment.

A human approval callback may authorize an `ask` action. It cannot override a deterministic `block` in this process.

### Typed decision plane role

The configured typed decision backend handles bounded judgment where a hard rule alone is too coarse: estimated destructiveness, human-review probability, completion support, judgeability, relevance, and retention. For shell actions it receives a redacted semantic command (not merely a hash), so the risk decision has the information it needs without intentionally forwarding common credential literals.

That makes the model a **decision plane**, not a security boundary or authorization credential.

## 8. Audit

`AuditLog` is append-only JSONL. To reduce data leakage:

- provider secrets are redacted;
- decision state is hashed instead of copied into the log;
- model tool calls log names + argument keys, not file content;
- shell commands log SHA-256 + byte count rather than the command string;
- verifier output remains evidence and is locally stored, with known credential patterns redacted.

For stronger production provenance, the JSONL writer is the seam to replace with Aftergraph Evidence / OpenTelemetry / signed receipts.

## 9. Paired control-plane ablation

The Hermes benchmark isolates the decision plane by enforcing an identical frontier generator signature across every condition before execution. The initial paired experiment keeps `qwen-3.8-max-thinking` fixed for code generation and compares:

```text
Qwen control: Qwen typed decisions → Qwen generation → verifier
Jev control:  Jev typed decisions  → Qwen generation → verifier
```

Each broken fixture is copied into a fresh workspace. Its deterministic verifier must fail before the agent runs, preventing already-green fixtures from inflating VSR. Conditions are shuffled deterministically per case/repeat. Raw mission metrics and redacted audit evidence are persisted separately from the aggregate report.

The benchmark reports VSR and false-completion claims, but does not infer monetary CPVO when the provider exposes only flat-subscription billing. Token-based control-plane tax remains measurable without inventing a per-token price.

## v1.3 Context, Proof, and Verification Fabric

The v1.3 slice adds three explicit planes around the existing intelligence scheduler.

```text
selected candidates
  → ContextCompiler
  → ContextProjection
  → frontier session
  → effects
  → VerificationPortfolio
  → EvidenceClaim
  → ProofGraph
  → MissionAcceptance
```

`ContextCompiler` consumes semantic scope scores but never grants authority. `ProofGraph` records what exact subject was verified and invalidates claims transitively when dependencies drift. `VerificationPortfolioOptimizer` chooses the cheapest configured method set satisfying a hard assurance floor and detection threshold. The optimizer's independence assumption is deliberately explicit and replaceable by empirical joint-failure data later.

The architectural invariant remains: **cognition proposes, authority admits, execution changes state, evidence observes, and mission acceptance requires fresh proof.**


## v1.4 bounded learning plane

The learning plane is downstream of observed outcomes and upstream of future routing. It has no authority-granting path.

```text
observed governed mission/decision
  → DecisionDistillationCompiler
  → LearningCandidate
  → replay
  → shadow
  → experimental
  → holdout
  → PromotionPolicy
  → promoted competence observation
  → future IntelligenceBid materialization
```

`CounterfactualReplay` is intentionally partial-observation-safe: it computes candidate VSR/CPVO only from shadow cases where the candidate's eventual verified outcome was actually observed. `VerifierCorrelationMatrix` prevents the verification planner from automatically treating correlated checks as independent. `ProofGraph.find_reusable` allows exact proof reuse only while all dependencies remain fresh. `SpeculativeFileTransaction` supports proof-aware speculative file work with delayed commit; it is not a general effect sandbox.


## v1.7 Distributed Verified Intelligence Fabric

The v1.7 reference kernel separates four concerns that ordinary multi-agent runtimes often collapse:

1. **Authority** — `AuthorityLedger` deterministically attenuates scope, budget, expiry and delegation depth.
2. **Work ownership** — `LeaseManager` assigns one current worker per node and fences stale workers with monotonic tokens.
3. **Mission scheduling** — `DistributedMissionRuntime` binds authority + capabilities + leases to `MissionGraph` states and bounded parallelism.
4. **Provider continuity** — `ProviderFailoverRouter` may change provider routes without silently changing logical model identity.

Authenticated receipts are a fifth, orthogonal plane: they can prove that a runtime holding a shared HMAC key emitted a particular canonical receipt, but they remain distinct from the `ProofGraph`'s independent verification semantics.
