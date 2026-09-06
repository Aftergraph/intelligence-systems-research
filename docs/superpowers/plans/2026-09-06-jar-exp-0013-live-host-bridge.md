# JAR-EXP-0013 Live Host Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:test-driven-development for production Python behavior and superpowers:verification-before-completion before any readiness claim.

**Goal:** Turn the verified research harness into an executable controlled-host bridge that can bind a real Windows Hermes installation, ToolRush, Chromium and Obscura to JAR-EXP-0013 without changing production runtime state.

**Architecture:** Add a small Python host bridge that validates exact treatment revisions, executes only explicit argv commands without `shell=True`, scrubs secret-like environment variables from persisted diagnostics, measures monotonic command duration, and emits machine-readable readiness output. A separate self-hosted GitHub Actions workflow targets a dedicated Windows runner label and invokes the bridge; GitHub-hosted runner timing remains non-authoritative.

**Tech Stack:** Python 3.11+, stdlib subprocess/json/pathlib/hashlib/time, pytest, existing JAR-EXP-0013 protocol/evidence modules, GitHub Actions self-hosted Windows runner.

**Spec:** `docs/superpowers/specs/2026-09-06-jar-exp-0013-runtime-acceleration-design.md`

## Global Constraints

- Experiment ID is exactly `JAR-EXP-0013`.
- ToolRush pin is exactly `4ecd8810fdc9e6e0c64af3d532f876d06f6a278e`.
- Obscura pin is exactly `a1e09de68c7617b8079fbb1661b0548c501971c1`.
- No `shell=True` execution.
- No secret values may be persisted in diagnostics or evidence.
- No production mutation is performed by the bridge.
- Self-hosted timing is authoritative only when preflight is clean and the configured host is the controlled Windows Hermes machine.
- GitHub-hosted runner timing is never authoritative performance evidence.

---

### Task 11.1: Host bridge contract

**Files:**
- Create: `experiments/runtime_acceleration/live_host.py`
- Test: `tests/runtime_acceleration/test_live_host.py`

**Interfaces:**
- `CommandResult(argv, returncode, stdout, stderr, duration_ms)`
- `run_argv(argv, *, cwd=None, env=None, timeout_s=60) -> CommandResult`
- `git_head(path) -> str`
- `require_revision(path, expected, label) -> str`
- `sanitize_environment(env) -> dict[str, str]`
- `build_obscura_serve_argv(executable, port=9222) -> list[str]`

TDD sequence: test import and behavior first; verify RED in CI; implement minimal behavior; verify GREEN.

### Task 11.2: Controlled-host probe CLI

**Files:**
- Create: `experiments/runtime_acceleration/controlled_host.py`
- Test: `tests/runtime_acceleration/test_controlled_host.py`

**Interfaces:**
- `probe_host(config, runner) -> dict` validates configured paths, exact source pins, ToolRush doctor smoke command, Obscura executable version/start command shape, and returns `READY`, `BLOCKED`, or `CONTAMINATED` without provider calls.
- `python -m experiments.runtime_acceleration.controlled_host --config <json>` prints one JSON result and exits non-zero unless state is `READY`.

### Task 11.3: Dedicated self-hosted execution workflow

**Files:**
- Create: `.github/workflows/jar-exp-0013-controlled-host.yml`
- Create: `experiments/runtime_acceleration/controlled-host.example.json`
- Modify: `experiments/runtime_acceleration/CONTROLLED_HOST_RUNBOOK.md`

**Workflow contract:**
- manual `workflow_dispatch` only;
- `runs-on: [self-hosted, Windows, X64, aftergraph-jar-exp-0013]`;
- verifies branch HEAD, installs only test dependencies, runs full JAR-EXP-0013 tests, runs controlled-host probe, uploads non-secret evidence artifact;
- never treats hosted-runner timing as performance evidence;
- no production deployment or mutation step.

## Verification

1. Observe RED from `pytest tests/runtime_acceleration/test_live_host.py -q` before production module exists.
2. Observe GREEN for the new unit tests after implementation.
3. Observe full `pytest tests/runtime_acceleration -q` GREEN on Ubuntu and Windows hosted CI for functional portability.
4. Validate workflow YAML and confirm the controlled-host job is manual and self-hosted-only.
5. Do not claim measured performance until a real runner with the required labels executes the controlled-host workflow and raw A/B/C/D evidence is analyzed.
