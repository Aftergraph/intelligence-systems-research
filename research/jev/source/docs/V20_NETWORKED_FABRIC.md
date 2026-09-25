# v2.0 — Verified Adaptive Intelligence Fabric

v2.0 turns the v1.9 signed node protocol into a real network-executed reference fabric while preserving fail-closed boundaries.

## What is newly executed

The bundled `jev-one v2-demo` opens a real TCP listener on loopback, wraps it in mutual TLS, authenticates each application message again with Ed25519, binds the TLS client common name to the signed request sender, performs a durable lease heartbeat, dispatches a bounded server-owned verification subprocess against the exact workspace hash, validates a hash-chained execution journal, applies an Ed25519-signed ProofGraph delta under compare-and-swap revision fencing, and requires verifier trust-domain diversity before accepting quorum.

```text
coordinator
   │ mTLS client cert + Ed25519 request
   ▼
NodeGatewayServer
   │ bounded OperationRegistry
   ├── lease_heartbeat
   └── verify_candidate
          │
          ▼
  hash-chained execution journal
          │
          ▼
  signed proof delta
          │
          ▼
 ProofGraph CAS revision
          │
          ▼
 diverse verifier quorum
```

## Dual authentication

Transport identity and application identity are separate controls:

1. TLS validates a CA-issued client certificate.
2. The application payload is independently Ed25519 signed.
3. When a peer certificate is present, its common name must equal the signed `sender` field.
4. NodeRequest nonces are replay protected for the lifetime of the gateway process.

The bundled CA helper is explicitly for local/reference execution. Production deployments should use an organization-managed PKI or workload-identity system. This package does not claim SPIFFE conformance.

## Bounded capability surface

The network caller sends an operation name and structured payload. The worker owns the operation registry and verifier command. No network request can register arbitrary code, select an executable, or ask for an arbitrary shell command. `PreconfiguredVerifierCapability` executes only the argv configured by the worker operator and rejects candidate hashes that do not match the worker workspace.

## Lease control

`LeaseControlService` exposes typed heartbeat and bounded renewal operations backed by `SqliteLeaseStore`. The sender must match the lease worker identity and the current fencing token must validate. A newer lease fences the old worker even if it still has a valid TCP connection.

## Execution trajectory integrity

`ExecutionJournal` is append-only and hash chained. It makes missing, reordered, or mutated execution observations detectable. Journal events are evidence inputs, not ground truth; they still require independent verification and mission acceptance.

## Signed proof replication

`SignedProofReplicator` signs ProofDelta payloads with Ed25519 before replication. The receiver checks the signer, payload integrity, graph id and base revision before the existing optimistic-concurrency apply. A stale but correctly signed writer is still rejected by the revision fence.

## Diverse quorum

`DiversityQuorumVerifier` can require both unique verifier principals and unique `trust_domain` metadata. Two verifiers inside one trust domain do not satisfy a two-domain policy. Negative evidence remains fail-closed when configured.

## Truth boundary

v2.0 proves a real local network socket and mutual-TLS path. It does **not** claim:

- deployment on Jonas-Lenovo or the VDS;
- a distributed-consensus database;
- production PKI or SPIFFE/OIDC conformance;
- arbitrary remote shell execution;
- live TypeSafe or Dialagram success from the build container;
- Byzantine fault tolerance merely because trust-domain diversity is enforced.

The live provider smoke was retried with runtime-only credentials on 25 September 2026. The build environment failed DNS resolution before authentication for both providers, so no provider-success claim is made.
