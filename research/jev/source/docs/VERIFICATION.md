# Verification — v2.0.0

Evidence cut: 25 September 2026.

## Fresh v2.0 gate

Observed in the build container:

```text
185 / 185 tests PASS
Python source statements: 5,856
Covered: 4,792
Missing: 1,064
Coverage: 81.83%
AST parse: 150 Python files PASS
compileall: PASS
source secret scan: PASS
ruff: UNVERIFIED_NOT_INSTALLED
```

`jev-one v2-demo` executed a real loopback TCP listener with mutual TLS, Ed25519-signed application messages, TLS peer-CN to signed-sender binding, a durable lease heartbeat, a fixed server-owned verification subprocess, a hash-chained execution journal, an Ed25519-signed ProofDelta, revision-fenced ProofGraph application and a two-trust-domain positive quorum. The demo explicitly reports `physical_multi_machine_executed: false`.

The final wheel was installed into a separate target directory and re-ran the same v2 demo successfully. Packaged `ExecutionEvent/v1` and `SignedProofDelta/v1` schemas were read from the installed wheel.

## Live provider boundary

A fresh authenticated smoke was attempted with the supplied TypeSafe and Dialagram credentials passed only through process environment. Both requests failed at DNS resolution (`Temporary failure in name resolution`) before authentication. No credential value is stored in this release and no live-provider-success result is claimed.

---

## Historical verification notes

Evidence cut: 24 September 2026.

This document records what was actually exercised in the release build environment. It deliberately separates local contract evidence from live-provider claims.

## Fresh local gate

Commands:

```bash
PYTHONPATH=src python -m pytest -q
python -m compileall -q src tests
./scripts/verify.sh
```

Observed result:

```text
51 passed in 7.11s
compileall: PASS
offline vertical demo: VERIFIED
example config doctor: PASS
frontier-only model listing: PASS
git diff --check: PASS
```

The zero-network demo performed a real repository edit in a temporary workspace, ran pytest inside the agent trajectory, then ran a fresh outer verifier and required the typed completion/judgeability gate before entering `VERIFIED`.

## Paired Hermes control-plane benchmark gate

The new benchmark manifest is:

```text
benchmarks/hermes_qwen_control_plane_ablation.yaml
```

It contains five deterministic broken SWE fixtures and two paired conditions:

```text
qwen-frontier-control:
  Qwen 3.8 Max Thinking -> typed decisions
  Qwen 3.8 Max Thinking -> coding generation

qwen-jev-control:
  TypeSafe Jev          -> typed decisions
  Qwen 3.8 Max Thinking -> coding generation
```

Fresh preflight evidence established:

```text
generator_invariant: true
cases: 5
conditions: 2
required credentials:
  DIALAGRAM_API_KEY
  TYPESAFE_API_KEY
```

Every bundled fixture was independently executed before the agent and its baseline verifier failed as intended. The runner refuses to execute an already-green fixture.

The current isolated build container does not expose either live credential, so authenticated execution correctly fails closed before any remote call. This is a blocked live-data gate, not a successful live benchmark.

On a Windows Hermes host the CLI can load only the allowlisted provider credentials from the profile dotenv without returning their values:

```powershell
jev-one benchmark-preflight benchmarks/hermes_qwen_control_plane_ablation.yaml --hermes-profile avc
jev-one benchmark benchmarks/hermes_qwen_control_plane_ablation.yaml --hermes-profile avc --repeats 3 -o benchmark-results/hermes-qwen
```

## OpenAI-compatible typed decision contract

`OpenAICompatibleDecisionBackend` uses an OpenAI-compatible `/chat/completions` endpoint and forces a `submit_decisions` function call. Local HTTP contract tests verify:

- forced tool selection;
- exact Choice/Score/Noul key coverage;
- local rejection of out-of-policy choices;
- normalized input/output usage accounting;
- Dialagram/Nexum base URL composition.

This adapter is the paired frontier-control condition for the Hermes ablation.

## Telemetry and benchmark metrics

Fresh tests cover normalization of provider usage from OpenAI Responses, OpenAI-compatible chat, Anthropic-style usage and Google `usageMetadata` shapes. Per mission the agent records:

- provider calls, input/output tokens and cached input tokens;
- typed-decision calls, input/output tokens and latency;
- tool calls;
- verifier runs and verifier latency;
- completion claims and completion claims caught by a failing verifier;
- wall time;
- token-based control-plane tax.

Aggregate definitions in v1.1.0 are explicit:

```text
VSR = VERIFIED missions / all missions
FCR = completion claims followed by failing deterministic verifier / completion claims
ControlPlaneTokenTax = decision-plane tokens / all measured model tokens
```

The package does not invent monetary CPVO when a provider is sold as a flat subscription without per-token billing attribution.

## Coverage

Command:

```bash
PYTHONPATH=src python -m pytest --cov=jev_engineering --cov-report=term -q
```

Observed:

```text
51 tests passed
TOTAL: 1879 statements, 508 missed, 73% line coverage
```

The CLI command bodies remain largely outside unit coverage; the CLI paths are exercised separately through smoke commands and benchmark preflight.

## Provider/transport contract tests

Local deterministic tests cover:

- OpenAI Responses coding transport;
- OpenAI Responses typed decision backend;
- OpenAI-compatible chat coding transport;
- OpenAI-compatible typed decision backend;
- TypeSafe/Jev `POST /v1/systemone` typed-answer parsing;
- Anthropic tool continuation;
- Google function-call continuation;
- LiteLLM arbitrary provider/model routing;
- frontier filtering before typed model choice;
- imported catalog entries failing closed as `unclassified`.

These are protocol/contract tests, not claims that every remote provider endpoint was contacted.

## Security/authority regression evidence

Tests cover:

- workspace path escape rejection;
- catastrophic shell hard-deny before probabilistic judgment;
- external publish/push-like actions requiring explicit approval;
- provider/TypeSafe secrets absent from spawned shell environments;
- allowlisted Hermes dotenv loading without returning secret values;
- redaction of common secret fields/patterns in JSONL audit output;
- completion requiring fresh verifier evidence rather than model self-report.

## Not verified in this environment

The release does **not** claim the following as live evidence:

- authenticated Dialagram/Nexum execution in this build container;
- authenticated TypeSafe/Jev production API calls in this build container;
- authenticated OpenAI production execution;
- live execution through every LiteLLM provider;
- OS/kernel sandboxing, network namespace isolation, or signed/tamper-evident evidence storage.

## Final wheel artifact

```text
wheel: aftergraph_jev_engineering-1.1.0-py3-none-any.whl
sha256: d1b0bd8d73e0ac54bdbd8af4d2dd7e506c22e784931e9b32d75c164a3b79e78b
import: PASS
version: 1.1.0
CLI demo from installed wheel: VERIFIED
```

## v1.3 verification surfaces

The v1.3 release adds three fresh evidence surfaces:

1. `ContextProjection` is emitted before frontier session creation when the compiler is enabled. It records candidate tokens, selected tokens, exclusion reasons, compression ratio and estimated useful-context ratio.
2. `ProofGraph` persists subject-bound `EvidenceClaim` objects. A workspace dependency change marks affected claims stale and propagates staleness through parent-child evidence edges.
3. `VerificationPlan` is selected before verifier execution when the verification fabric is enabled. Every method in the selected portfolio must pass; otherwise the combined verifier exit is non-zero and mission acceptance cannot be minted.

The detection-probability composition currently assumes independent verifier failures. This is an explicit planning approximation, not measured evidence. Production calibration should replace it with joint/correlated failure estimates when available.

## v1.7 fresh release gate — 2026-09-25

The v1.7 distributed-runtime slice was verified locally from the release source tree.

- full pytest suite: **146/146 PASS**;
- v1.7 focused tests: authority attenuation, worker leases/fencing, distributed MissionGraph runtime, provider failover, signed receipts, automatic learning campaigns, packaged contracts, and CLI vertical demo all PASS;
- coverage: **3,628 / 4,484 statements covered = 80.91%**;
- `compileall`: PASS;
- AST parse: PASS across 102 source/test Python files;
- provider-secret release scan: PASS;
- offline `jev-one distributed-demo`: PASS with two parallel branches, speculative join, transient same-logical-model provider failover, synthetic campaign promotion, and HMAC receipt verification;
- wheel build: PASS using local `pip wheel --no-build-isolation` because external package index DNS was unavailable;
- target install from wheel: PASS;
- packaged v1.7 schemas: PASS;
- installed-wheel `distributed-demo`: PASS;
- extracted-wheel secret scan: PASS.

Live provider smoke was attempted with the operator-supplied TypeSafe and Dialagram credentials injected only through the process environment. Both checks stopped at DNS resolution (`Temporary failure in name resolution`) before authentication. Therefore authenticated provider success remains **UNVERIFIED** in this build environment.

`ruff` remains **UNVERIFIED_NOT_INSTALLED**. No lint PASS claim is made.