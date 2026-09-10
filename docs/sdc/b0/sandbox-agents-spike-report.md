# SDC-B0 Spike Report — OpenAI Sandbox Agents Execution-Backend Adapter

**Status:** SPIKE COMPLETE (experimental, beta) · **Issue:** #59 · **Parent:** #54
**Evidence class:** Engineering experiment only — NOT STUDY-012 confirmatory evidence.
**Date:** 2026-09-10 · **Branch:** `spike/sandbox-agents-spike-eval`
**Adapter:** `src/sdc_b0/openai_sandbox_adapter.py` (subclasses canonical `WorkerSandbox` ABC)
**Tests:** `tests/test_openai_sandbox_adapter.py` — 7/7 pass (live SDK, offline, no credentials)

## Pinned SDK version

`openai-agents==0.22.2` (installed; transitive `openai==3.11.0`). Verified via
`agents.sandbox` module introspection on the VDS. API surface used:
`BaseSandboxClient.create(manifest)`, `SandboxSession.exec`, `aclose`,
`UnixLocalSandboxClient`, `Manifest(users, network_enabled)`, `User`,
`LocalSnapshot` persist/restore. The SDK surface is **beta** and shifted
between versions (e.g. `agents.sandbox.snapshot` is a module, not a package).

## Per-question answers (observed, SDK 0.22.2, UnixLocal backend)

1. **Scoped filesystem?** PARTIAL. `Manifest(root, users, network_enabled)` declares
   scope; the UnixLocal backend materialises it as a host temp dir. There is no
   container/mount boundary on this backend — scope is declarative, not enforced.
2. **Resumable sessions?** SDK-side YES (`create/resume/serialize/deserialize_session_state`
   exist on `BaseSandboxClient`), adapter-side NO — the canonical ABC has no
   resume method, so resume is not reachable through the `WorkerSandbox` surface.
3. **Snapshot recovery?** SDK-side YES (`LocalSnapshot.persist/restore` are file
   copy-out/copy-in). Same ABC gap as (2): deterministic worker restart via
   snapshot is not expressible without changing the orchestration contract,
   which this spike must not do.
4. **Command capture?** YES. `exec` returns `exit_code/stdout/stderr` (bytes);
   the adapter decodes to `SandboxResult`. Hermes captures everything externally.
   Verified live (`echo`, failing `ls`).
5. **Secret isolation?** WEAK. `UnixLocalSandboxClient` defaults to
   `inherit_host_environment=True` with no allowlist set by the adapter; host env
   (including any secrets) is visible inside the session unless the caller
   configures the allowlist. HermesWorktreeSandbox inherits env too, but its
   threat model is worktree isolation, not secret containment — neither backend
   gives model-invisible secret storage.
6. **Network restriction?** DECLARED, NOT ENFORCED (local backend).
   `network_enabled=False` is passed in the manifest, but the UnixLocal backend
   performs no netns/iptables isolation — the session shares host networking.
   A remote/container backend might enforce it; untested here.
7. **Unprivileged user support?** DECLARED, NOT VERIFIED. `users=[User(name='worker')]`
   is passed, but the local backend was not observed switching uid. Treat as
   manifest metadata on this backend.
8. **Swappable without changing the task contract?** YES. The adapter is a
   drop-in `WorkerSandbox` subclass (`create/execute/teardown/list_active`
   verified live). The ABC, `HermesWorktreeSandbox`, and orchestration are untouched.

## Comparison against HermesWorktreeSandbox baseline

| Dimension | HermesWorktreeSandbox (canonical) | OpenAI adapter (spike) |
|---|---|---|
| Isolation primitive | git worktree per task | SDK session in host temp dir |
| base_sha / stale-base semantics | real (git) | none — SHA recorded in env-var hack |
| Offline / deterministic | yes | yes (local backend) |
| Snapshot / resume via ABC | n/a (fresh worktree = recovery) | not reachable via ABC |
| Secret isolation | none claimed | none achieved (env inherited) |
| Network isolation | none | declared, unenforced locally |
| API stability | stable (git CLI) | beta, shifting imports |
| Host trust requirement | full host trust | full host trust (local backend) |

The adapter adds dependency and API-churn risk while providing **no**
isolation property the baseline lacks — and it **loses** the baseline's real
git semantics (base_sha, stale-base invalidation), which are load-bearing for
the SDC reconciliation design.

## Recommendation: REJECT for B0 inclusion

Keep `HermesWorktreeSandbox` canonical. Retain this adapter + tests as an
experimental reference only. Revisit only if (a) the SDK surface stabilises,
(b) a backend with enforced filesystem/network/user isolation is evaluated
(not the local backend), and (c) snapshot/resume can be exposed without
changing the Hermes-owned `WorkerSandbox` ABC. Do not promote Sandbox Agents
to canonical runtime. Do not cite this spike as study evidence.
