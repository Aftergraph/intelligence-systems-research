# v1.8 Networked Verified Intelligence Fabric

v1.8 moves the v1.7 in-process distributed kernel toward an identity-bound, crash-durable reference fabric. It deliberately stops short of claiming a production distributed consensus system or live remote transport.

## Boundaries

The reference path is:

```text
WORKS ExecutionContext
        ↓
Ed25519 workload assertion
        ↓
TrustGatewayValidator
  identity + context + authority
        ↓
WorkerDirectory
        ↓
SqliteLeaseStore
  durable lease + fencing token
        ↓
MissionGraph execution
        ↓
SqliteProofGraphStore
  optimistic revision fencing
        ↓
independent verifier claims
        ↓
QuorumVerifier
        ↓
Mission commit
        ↓
Ed25519 public-key receipt
```

## What is real in this release

- Ed25519 signatures use `cryptography` and can be verified with only the public key.
- workload assertions bind principal, audience, execution context, issue time, expiry and nonce;
- Trust Gateway admission binds workload identity to the exact WORKS execution context and an active authority grant;
- worker leases survive process restarts in SQLite and use monotonic fencing per mission node;
- proof graph snapshots use compare-and-swap revisions so stale writers fail closed;
- quorum verification counts unique verifier principals and can reject conflicting negative evidence;
- provider routes can be protected by a closed/open/half-open circuit breaker;
- Aftergraph worker endpoints can be registered and selected by health and capability.

## What is not claimed

- `aftergraph://...` endpoint URIs are identifiers, not a network transport implementation;
- SQLite is the durable reference backend, not a cross-datacenter consensus database;
- workload assertions are Aftergraph-native Ed25519 assertions, not certified SPIFFE SVIDs or OIDC tokens;
- `TrustGatewayValidator` is a local adapter contract, not a deployed Trust Gateway service;
- public-key signatures prove key possession/integrity, not independent truth;
- quorum only becomes independent evidence when verifier principals are genuinely operationally independent;
- no authenticated TypeSafe/Dialagram benchmark is implied by the offline v1.8 demo.

## Production substitution seams

The reference interfaces are intentionally replaceable:

- `SqliteLeaseStore` → transactional/consensus lease service;
- `SqliteProofGraphStore` → durable shared evidence store;
- `WorkerDirectory` → Aftergraph node/runner registry;
- `WorkloadIdentityVerifier` → SPIFFE/OIDC/workload identity adapter;
- `TrustGatewayValidator` → live Trust Gateway admission client;
- endpoint identifier → Runtime/WORKS transport.
