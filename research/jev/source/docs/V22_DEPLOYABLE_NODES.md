# v2.2 Deployable Aftergraph Nodes

v2.2 turns the v2.1 loopback multi-node proof into a deployable node process with persistent identities and file-based runtime configuration.

## Security invariants

- TLS is mandatory for non-loopback HTTP transport.
- mTLS peer identity is bound to the Ed25519-signed request sender.
- Node Ed25519 private keys are runtime files and must not be committed.
- Remote callers can invoke only registered bounded operations.
- `verify_candidate` uses a server-owned fixed argv and never accepts a remote shell command.
- Durable lease fencing remains mandatory for verification work.
- Provider API keys remain environment/runtime secrets and are not part of node config.

## Bootstrap

Generate node signing material:

```bash
jev-one node-keygen --key-id worker:jonas-lenovo -o /etc/aftergraph/node.ed25519.key
```

Generate a secret-free node config template:

```bash
jev-one node-template --node-id worker:jonas-lenovo -o /etc/aftergraph/node.json
```

Validate before serving:

```bash
jev-one node-doctor /etc/aftergraph/node.json
```

Serve:

```bash
jev-one node-serve /etc/aftergraph/node.json
```

The coordinator uses a separate client config and key:

```bash
jev-one node-client-template \
  --sender-id coordinator:aftergraph \
  --worker-id worker:jonas-lenovo \
  --endpoint-url https://node.example:9443/v1/node/call \
  -o coordinator-node.json
jev-one node-probe coordinator-node.json
```

A successful `node-probe` proves the TLS handshake, client certificate, application Ed25519 signature, responder signature, recipient binding and bounded `node_describe` operation.

## Truth boundary

`v22-demo` executes the full deployable configuration path on one host over a real TCP+mTLS socket. Physical Jonas-Lenovo ↔ VDS execution requires provisioning these configs/certificates/keys on those hosts and exposing a mutually reachable network path.
