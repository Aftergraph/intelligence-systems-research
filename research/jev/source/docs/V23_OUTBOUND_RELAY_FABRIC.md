# v2.3 Outbound Relay Fabric

## Why this exists

v2.2 makes an Aftergraph node deployable, but a direct inbound listener is often the wrong physical-network assumption for laptops, NATed workers, roaming devices, or hosts behind restrictive firewalls. v2.3 adds a relay seam so a worker can establish an authenticated **outbound-only** connection to a reachable relay while preserving the end-to-end signed node protocol.

The relay solves network reachability. It does **not** become execution authority.

```text
Coordinator
    |
    | mTLS to relay
    | signed NodeRequest (Ed25519)
    v
Relay Hub
    |
    | generation-fenced registered worker session
    v
Worker outbound mTLS connection
    |
    | signed NodeRequest verified end-to-end by worker
    v
Bounded NodeGateway
    |
    +-- lease_issue (authorized issuer only)
    +-- lease_heartbeat / lease_renew
    +-- verify_candidate (server-owned argv only)
    +-- journal_poll (fenced lease required)
    +-- node_describe
```

## Security invariants

1. The worker opens the network connection. No inbound worker port is required.
2. Relay registration is bound to the worker mTLS certificate common name.
3. Coordinator access to the relay is bound to an explicit mTLS coordinator allowlist.
4. The worker still verifies the original Ed25519 `NodeRequest`; the relay cannot mint a valid coordinator request.
5. `NodeGateway.sender_key_bindings` binds a claimed application sender to an allowed signing key. This closes the identity gap that appears when the direct coordinator certificate is not present on the relay-to-worker hop.
6. Duplicate worker registration increments a relay session generation and fences/closes the older stream.
7. The remote lease issuer must be allowlisted and signing-key-bound.
8. Lease capabilities are an allowlisted subset and `verify_candidate` checks that the current fenced lease actually grants that capability.
9. Strict node deployments require fenced lease binding for journal polling.
10. The remote caller never supplies verifier argv and no generic network `shell` capability is exposed.

## Remote lease admission

A physically remote coordinator cannot write the worker's local SQLite lease database. v2.3 therefore adds a bounded `lease_issue` operation. It is disabled unless `lease_issuer_ids` is configured.

The issuer can request only capabilities from `lease_allowed_capabilities`, cannot set the fencing token, and cannot exceed `lease_max_ttl_s`. The node assigns the monotonic fencing token transactionally.

## Receipt/stream identity

Earlier streaming and receipt journals were independently timestamped copies of the same logical events. v2.3 makes the streamed journal append the exact already-minted `ExecutionEvent` objects from the receipt journal. The receipt-carried journal head and the remotely polled stream head must therefore be identical.

This matters because two semantically similar logs are not the same evidence object.

## Deployment modes

### Direct node

```bash
jev-one node-serve /etc/aftergraph/node.json
```

Requires an inbound reachable node endpoint.

### Outbound-only relay node

On a reachable relay host:

```bash
jev-one relay-hub-serve /etc/aftergraph/relay-hub.json
```

On the worker:

```bash
jev-one relay-node-serve /etc/aftergraph/relay-node.json
```

On the coordinator:

```bash
jev-one relay-probe /etc/aftergraph/relay-client.json
```

Templates:

```bash
jev-one relay-hub-template -o relay-hub.json
jev-one relay-node-template -o relay-node.json --node-config-file node.json
jev-one relay-client-template -o relay-client.json --sender-id coordinator --worker-id worker:jonas-lenovo
```

All templates contain paths/placeholders only. They do not contain provider keys, TLS private keys, or Ed25519 private keys.

## Reference proof

```bash
jev-one v23-demo
```

The demo executes a real TCP relay path on one host with mutual TLS on both network sides, end-to-end Ed25519 request/response signing, application sender-key binding, remote lease issuance, a real fixed verifier subprocess, fenced journal polling, and identical receipt/stream journal heads.

## Truth boundary

The v2.3 demo proves the relay protocol and deployment seam on one physical host. It does **not** claim that Jonas-Lenovo and the VDS were physically connected in the release build. The available remote desktop connector was quota-blocked during this build, so physical deployment was not fabricated. The outbound relay architecture is the implemented solution to that reachability/control-plane wall.
