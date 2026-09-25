# v1.9 — Signed Aftergraph Node Transport

v1.9 closes the largest truth boundary left by v1.8: worker endpoints are no longer only identifiers. The release adds a bounded application protocol that can be carried over HTTPS or an Aftergraph-native transport adapter.

## Protocol

`NodeRequest/v1` and `NodeResponse/v1` are signed with Ed25519 receipts. A request binds:

- request ID;
- sender and recipient principals;
- bounded operation name;
- structured JSON payload;
- send timestamp; and
- replay nonce.

The receiver verifies signature, recipient and nonce before dispatching a typed handler. Remote HTTP requires HTTPS; plain HTTP is accepted only for loopback tests.

## Remote work order

`RemoteWorkOrder/v1` binds a mission/node execution to the exact:

- WORKS execution-context ID;
- lease ID;
- fencing token;
- authority grant ID; and
- candidate SHA.

`RemoteWorkReceipt/v1` must echo that binding and is rejected if any field differs. The reference protocol exposes no generic shell operation.

## Proof replication

`ProofDelta` applies evidence to a shared ProofGraph only when its `base_revision` matches the destination store. Concurrent/stale deltas fail closed rather than overwriting newer proof state.

## Truth boundary

The reference HTTP transport is implemented and tested with a real `httpx` transport seam, including the full signed serialization path. The release does **not** claim that a real Jonas-Lenovo or VDS network listener has been deployed. The bundled `transport-demo` is zero-network and demonstrates the protocol, signature boundary, work-order binding and proof replication without opening a socket.
