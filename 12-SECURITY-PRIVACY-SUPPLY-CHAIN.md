# Security, Privacy and Supply Chain

## Threat families
- prompt/goal injection
- tool misuse
- capability confusion
- identity/privilege abuse
- delegation forgery
- registry poisoning
- supply-chain compromise
- unexpected code execution
- memory/context poisoning
- verifier compromise
- evidence tampering
- trajectory manipulation
- cascading failures
- secrets exposure

## Filesystem policy
Must eventually define:
read, write, execute, delete, move, mounts, symlinks, traversal, temp directories, generated artifacts, ownership, remote files, secrets and platform differences.

## Network policy
Need explicit behavior for:
DNS, redirects, private ranges, metadata endpoints, proxies, callbacks, WebSockets, TLS and egress quotas.

## Secrets
Secrets must be references, not ordinary context values.

Need:
provider reference, non-exportability, scope, TTL, rotation, redaction and audit.

## Data governance
Need:
classification, external-model rules, retention, region constraints, memory persistence, minimization and selective disclosure.

## Supply chain
Represent:
models, datasets, skills, tools, MCP servers, agents, policies, prompts/configuration and code.

Prefer mapping into established BOM/provenance systems rather than inventing another universal format.

## Privacy/evidence tension
Evidence must not become “retain everything forever.”
Research must optimize for minimum sufficient evidence.
