# Security

## v2.6 efficiency-planning boundary

`SystemEfficiencyCompiler` is not an authority source and cannot promote routes, disable verification, or authorize external effects. `EarlyExitGate` requires an already-verified cheap path and fails closed for higher risk, higher assurance, or insufficient predicted VSR. Optimization levers are filtered by evidence level; modeled or hypothetical reductions cannot silently become observed evidence.


## v2.4 resilience and campaign boundaries

- Relay session generations can be persisted in SQLite so a relay restart does not silently reset generation fencing. SQLite is a single-store reference, not multi-relay consensus.
- Resumable journal checkpoints persist only cursor/hash continuation state. They do not turn checkpoints into authoritative evidence and reject rollback/hash discontinuity.
- Physical-pair manifests contain file references and public configuration only; credentials and private keys remain external files/runtime secrets.
- `live-campaign` resolves provider credentials at runtime and requires operator-supplied pricing; no API key or provider price is embedded in the release.
- A physical-pair doctor result proves configuration coherence, not physical reachability or execution.
- No arbitrary remote shell is introduced in v2.4.

# Security model

This is a local coding-agent harness, not an operating-system sandbox.

## Enforced by the package

- All file tools are constrained to the configured workspace root.
- Absolute paths and `..` escapes are rejected.
- Known catastrophic shell commands are blocked deterministically before any AI decision.
- Default `verify_only` command mode rejects shell chaining/substitution/redirection and absolute/parent-path arguments before command execution.
- Known external/consequential mutations require explicit human approval.
- Provider/API credentials are removed from the shell environment.
- `VERIFIED` requires a fresh operator-configured verifier command and completion gate.
- Audit logging minimizes raw decision/source/tool payload storage and redacts known credential patterns.
- The configured typed decision backend sees redacted command semantics for ambiguous shell risk decisions; common key/token/password literals are removed before the decision request.
- Optional Hermes dotenv loading is allowlisted to Dialagram/Nexum and TypeSafe credential names; the loader returns presence only, never secret values, and does not overwrite an existing process credential unless explicitly requested.

## Not provided by this package

- kernel/VM/process sandboxing;
- syscall filtering;
- network namespace isolation or egress firewalling;
- a complete shell sandbox in `command_mode: full` (that mode intentionally expands the action surface);
- a secret broker for arbitrary tools;
- a complete tamper-evident audit ledger (v1.8 adds signed receipts, not a full signed audit log);
- production-grade distributed consensus for relay generations/proof state, managed PKI federation, or independently operated physical-node deployment evidence.

For consequential workloads, run the harness inside an isolated Aftergraph Habitat/worker boundary or equivalent container/VM sandbox and broker external credentials outside the frontier model process.

## Reporting

Do not include live credentials in bug reports, logs, screenshots, or test fixtures.

## v1.3 evidence and verification boundaries

- Evidence freshness is dependency-bound. Persisted claims are invalidated when the observed workspace hash differs from the hash bound into the claim.
- A passing verifier claim does not itself grant authority or imply mission acceptance; the completion gate mints a separate child claim.
- Verification portfolio probabilities are planning inputs, not security guarantees. High-consequence deployments should derive them from measured verifier performance and correlation, not illustrative priors.
- Proof files contain hashes, predicates, verifier metadata and outcomes, but must not contain provider credentials or raw secrets. Existing audit redaction rules still apply.
- `$PRIMARY_VERIFY` resolves only to the operator-provided verifier command and is still subject to deterministic `verify_only` command policy.

## v1.4 learning and speculation boundaries

- Learning candidates cannot skip the ratchet. Promotion is a separate policy decision; a candidate's existence does not grant authority or change a production route.
- Shadow/counterfactual results do not infer missing outcomes. Unobserved candidate outcomes remain unknown.
- Competence updates are keyed observations, not universal model ratings. Operators should choose keys that encode material task/environment differences.
- Correlation-adjusted verification probabilities are planning estimates. High-assurance deployments should calibrate them from independent defect-injection evidence.
- `SpeculativeFileTransaction` stages **file writes only** and does not isolate arbitrary code execution. It must not be treated as a VM/container security boundary.
- Speculative commit requires fresh passing prerequisite proof and unchanged file preimages; external side effects are intentionally outside this primitive.


## v1.5 shadow-routing and effect-transaction boundaries

- A shadow decision backend never controls execution before promotion. Candidate exceptions are observational and cannot force a fallback path.
- A promoted decision-family route is activated only from a `PROMOTED` learning candidate. Promotion itself requires the configured VSR/FCR/CPVO and replay/shadow/experiment/holdout gates.
- If a promoted candidate backend fails, the decision fails closed; v1.5 does not silently route back to the old incumbent and hide the regression.
- Shadow logs store decision outputs, not raw decision inputs. Scope records omit source excerpts so repository contents and credentials are not duplicated into the shadow ledger.
- `FileEffectTransaction` is a reversible **repository file-write adapter**, not an external transaction coordinator. It does not make shell, network, deployment, billing, IAM or email effects reversible.
- Compensation is allowed only while the target still equals the transaction's exact postimage. Workspace drift blocks compensation rather than overwriting newer work.
- Effect verification requires fresh positive proof bound to the exact post-effect SHA-256 subject.


## v1.6 provider-secret, HTTP-effect and learning boundaries

- Provider credentials are runtime inputs only. Real TypeSafe/Dialagram keys must never be committed, copied into YAML, packaged into a wheel/ZIP, or written into evidence/audit artifacts.
- `.env.example` contains names only. Real dotenv files are ignored by Git and local helper-created files are mode `0600` where the platform permits it.
- The release secret scanner recognizes provider-specific key shapes and fails the release when they appear in tracked/release files.
- GitHub Actions uses `secrets.*`, not `vars.*`, and the live provider workflow is manual-only plus environment-scoped. Environment review/protection is an operator setting, not something the source repository can guarantee by itself.
- `HttpJsonEffectTransaction` requires HTTPS and an explicit host allowlist. It does not accept arbitrary URLs selected by a model. Verification is bound to the external readback hash.
- HTTP compensation is only attempted when an explicit compensation method/URL/payload was prepared; the runtime never assumes a remote API is reversible.
- Statistical promotion is not authority. A promoted route remains subject to existing deterministic authority/tool/effect gates and can be quarantined on regression.
- Mission-graph speculation permits early computation, not early external-effect commitment.


## v1.7 distributed-authority, lease, failover, and receipt boundaries

- An `AuthorityGrant` can only attenuate scope, expiry, delegation depth, and conservatively available budget. It does not mint authority from model output.
- `WorkerLease` fencing prevents stale workers from committing through the reference runtime after reassignment; it is not a distributed consensus protocol and does not protect external systems that ignore the fencing token.
- Lease heartbeat/expiry are runtime guards, not remote workload identity. Production worker identity should be bound to Aftergraph Habitat/Trust Gateway or another authenticated execution substrate.
- Provider failover preserves logical-model identity by default. Cross-model substitution and auth failover are explicit policy choices because they may change semantics or hide credential/configuration faults.
- HMAC-SHA256 receipts provide shared-secret integrity/authenticity only. They must not be represented as independent signatures, non-repudiation, hardware attestation, or third-party evidence.
- Receipt signing keys must be injected at runtime and excluded from model context, source control, release archives, audit payloads, and evidence graphs.
- Automatic learning-campaign phase progression does not grant execution authority and cannot bypass the underlying statistical promotion policy.


## v1.8 networked identity, durable-state and quorum boundaries

- Ed25519 workload assertions and public-key receipts are cryptographic reference primitives. Private signing keys must remain outside model context, source control, release archives, logs and evidence payloads.
- The workload assertion binds principal, audience, execution-context ID and time validity. It is Aftergraph-native and must not be represented as SPIFFE/OIDC conformance without a real standards adapter and conformance evidence.
- `TrustGatewayValidator` is a local fail-closed admission contract. Production deployment must bind it to the actual Trust Gateway policy/identity service rather than treating this local object as a network security perimeter.
- `SqliteLeaseStore` provides crash durability and transactional fencing inside one SQLite database. It is not a distributed consensus protocol and should be replaced by a transactional/consensus store for multi-host production.
- `SqliteProofGraphStore` uses optimistic revision fencing to reject stale proof writes. It does not by itself provide Byzantine replication, multi-region durability or third-party timestamping.
- Quorum counts unique verifier principals, but distinct strings are not proof of operational independence. High-assurance configurations must bind verifier identities to separately controlled keys/habitats.
- Circuit breakers are availability controls, not quality guarantees. Recovery/half-open state never authorizes cross-model substitution or credential failover by itself.
- `WorkerDirectory` endpoint URIs describe discovery/admission metadata only in v1.8. No SSH/RPC/Aftergraph transport is opened by the reference implementation.

## v2.0 network identity boundary

The v2.0 node gateway can enforce mutual TLS and independently verifies Ed25519-signed application messages. When a client certificate is present, the certificate common name is bound to the signed request sender. This is defense in depth, not a substitute for production workload identity governance.

`EphemeralCertificateAuthority` is a test/reference helper. Do not persist or use its generated CA as an organization production root. Production deployments should use managed PKI/workload identity and a separately governed key lifecycle.

The remote operation surface is server registered. Do not add a generic network `shell`/`exec` operation; expose typed capabilities with explicit authorization, input validation, readback, and evidence instead.

## v2.1 additions

- Remote verifier execution requires a valid durable lease and exact fencing token before subprocess launch.
- Work order node and authority grant must match the fenced lease.
- Remote callers cannot choose verifier argv; commands remain server-owned fixed capabilities.
- Execution journal streaming is read-only and bounded by cursor/limit; remote callers cannot append events.
- Multi-node acceptance requires independent trust domains, not duplicate votes from one verifier domain.

## v2.2 deployable-node boundaries

- Persistent node signing keys and TLS private keys are runtime deployment secrets and must remain outside source control, model context, release archives and evidence payloads.
- `NodeAgent` exposes only registered typed operations. A generic network shell/exec capability is intentionally absent.
- Direct `node-serve` requires an inbound reachable endpoint and therefore must be protected by host firewalling and managed PKI in production.

## v2.3 outbound-relay boundaries

- The relay solves reachability, not authority. A registered relay session does not grant permission to execute work.
- Worker registration is bound to the mTLS certificate common name and an explicit relay node allowlist. Coordinator relay calls require an allowlisted coordinator certificate.
- The worker still verifies the original Ed25519 signed request. For relay deployments, `peer_sender_key_ids` binds the claimed sender identity to an allowed signing key so a different trusted key cannot impersonate the sender.
- Duplicate worker connections are generation-fenced; the newer registration closes the older socket. This is a relay-session fence, not a replacement for the mission/work lease fencing token.
- `lease_issue` is absent unless `lease_issuer_ids` is configured. Issuers can request only `lease_allowed_capabilities` and cannot choose the fencing token.
- `verify_candidate` requires that the current fenced lease explicitly grants `verify_candidate`. Strict deployable-node journal polling requires the same live lease, `journal_poll` capability, sender ownership and stream/lease binding.
- The relay hub terminates transport TLS and can observe routed encrypted-at-transport payloads, but it still cannot forge the end-to-end Ed25519 coordinator signature. If payload confidentiality from the relay itself is required, an additional end-to-end encryption layer is necessary.
- The relay implementation is a reference single-hub design, not Byzantine relay consensus, multi-region HA, or a DDoS perimeter.
- Physical multi-machine deployment was not executed in the v2.3 build environment; do not represent the one-host reference proof as Lenovo↔VDS evidence.
## v2.5 campaign-evidence boundaries

- Shadow and experiment measurements are development evidence. Only the reserved holdout slice may authorize a v2.5 promotion.
- A `CampaignEvidenceBundle` stores hashes and paths, never provider credentials. Secrets remain runtime-only and must not be copied into results, reports, manifests, or pricing files.
- Bundle SHA-256 integrity does not provide independent identity, timestamping, non-repudiation, or external attestation.
- A 10× feasibility ceiling is a mathematical bound under stated assumptions, not an observed performance result.
- Post-promotion monitoring may request quarantine; it does not independently revoke external authority unless the host runtime wires that signal into its promotion/authority controls.
- Do not weaken the holdout boundary by repeatedly inspecting and redesigning against the same holdout dataset. Replace contaminated holdout evidence with a newly preregistered set.

