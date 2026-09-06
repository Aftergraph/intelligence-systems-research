# JAR-EXP-0013 Controlled Windows Host Runbook

## Purpose

Execute authoritative JAR-EXP-0013 performance measurements on a real Windows Hermes host. GitHub-hosted runner timings are functional evidence only and MUST NOT be promoted as performance evidence.

The implementation harness may be complete while the experiment remains inconclusive. No performance or promotion claim is valid until controlled-host evidence exists and the preregistered analysis passes.

## Required host

Use the real Windows machine that runs Hermes and can execute the frozen Chromium, ToolRush, and Obscura treatments. Keep the machine on AC power and satisfy the frozen preflight limits before every confirmatory timing block.

## Frozen revisions

- ISR baseline: `f9fd62d57408308788822162d9ded7d9741dbb10`
- ToolRush: `4ecd8810fdc9e6e0c64af3d532f876d06f6a278e`
- Obscura: `a1e09de68c7617b8079fbb1661b0548c501971c1`

Do not silently update any treatment during the experiment. A changed treatment revision is a new experimental revision.

## Conditions

| Condition | Tool layer | Browser layer |
|---|---|---|
| A | Stock Hermes | Chromium |
| B | ToolRush | Chromium |
| C | Stock Hermes | Obscura |
| D | ToolRush | Obscura |

## Local-first operator path

Open elevated PowerShell in a checkout of `research/jar-exp-0013-runtime-acceleration`.

### Safe default: readiness + frozen plan only

```powershell
Set-Location <path-to-intelligence-systems-research>
.\experiments\runtime_acceleration\start-controlled-host.ps1
```

The safe default performs host preparation, verification, the authoritative local readiness probe, and freezes the deterministic Phase-1 schedule. It deliberately does **not** start measured A/B/C/D treatments.

### Explicit Phase-1 measurement execution

After reviewing the `READY` probe and frozen schedule, explicitly opt into the measured trace replay:

```powershell
.\experiments\runtime_acceleration\start-controlled-host.ps1 -RunPhase1
```

`-RunPhase1` executes the frozen 20 paired blocks × 4 conditions = 80 planned Phase-1 runs. The switch is intentionally required so a routine readiness check cannot accidentally create performance observations.

## What `start-controlled-host.ps1` does

The script:

1. requires Administrator privileges and Python 3.11;
2. creates an isolated harness venv at `C:\Aftergraph\JAR-EXP-0013\harness-venv`;
3. installs research test dependencies, `psutil`, and the pinned Python Playwright client into the harness venv, not the Hermes application environment;
4. runs the complete `tests/runtime_acceleration` suite and stops on any failure;
5. fail-closes if configured Hermes, ToolRush, Obscura, or Chromium runtime paths are missing;
6. creates an isolated benchmark workspace at `C:\Aftergraph\JAR-EXP-0013\workspace` and writes the deterministic tool fixture outside measured timing;
7. writes a machine-local, non-secret `controlled-host.json` containing the exact runtime paths;
8. runs `experiments.runtime_acceleration.controlled_host` and writes `controlled-host-probe.json`;
9. exits non-zero unless probe state is exactly `READY`;
10. freezes the deterministic Phase-1 A/B/C/D order using 20 paired blocks and seed `130013`;
11. stops before measurement unless `-RunPhase1` was supplied;
12. with `-RunPhase1`, invokes `experiments.runtime_acceleration.phase1_host_run` with the exact config, probe, protocol, plan, evidence root, and unique execution id.

The host configuration includes these runtime fields in addition to the read-only probe paths:

- `hermes_python`
- `hermes_root`
- `workspace`
- `toolrush_repo`
- `toolrush_doctor`
- `toolrush_plugin`
- `obscura_repo`
- `obscura_executable`
- `chromium_executable`

If local paths differ, provide the corresponding PowerShell parameters explicitly. The config MUST NOT contain credentials, provider tokens, cookies, or other secrets.

## Phase-1 runtime composition

`phase1_host_run` fail-closes before starting treatments unless the host probe is `READY` and ToolRush/Obscura pins match the frozen protocol.

For each controlled execution it:

- starts one loopback-only deterministic fixture server;
- starts one persistent stock Hermes worker;
- starts one separate persistent ToolRush Hermes worker;
- uses equal JSONL request/response transport for the two Hermes lanes;
- launches a fresh Chromium backend for each A/B run that requests one;
- starts a fresh Obscura loopback CDP server and connects with Playwright `connectOverCDP` semantics for each C/D run that requests one;
- restricts benchmark browser navigation to the loopback fixture origin;
- executes the frozen run order without fallback substitution;
- closes each per-run browser adapter exactly once;
- always closes both persistent Hermes workers when the execution scope exits.

If treatment execution or cleanup fails, the affected run is recorded as an execution error and its timing is not preserved as valid performance evidence.

## Optional self-hosted GitHub Actions path

The repository also supports a dedicated self-hosted runner for centrally triggered reproduction:

```powershell
.\experiments\runtime_acceleration\start-controlled-host.ps1 -DispatchWorkflow
```

This path is optional and separate from `-RunPhase1`. Only it requires authenticated `gh`. The dedicated runner uses all four labels:

- `self-hosted`
- `Windows`
- `X64`
- `aftergraph-jar-exp-0013`

`bootstrap-self-hosted-runner.ps1` pins GitHub Actions runner `2.337.0` and verifies the Windows x64 archive against SHA256 `1150692afa94e71f872017e254ea55b6eece1eece3fe7e3a6d4c93d0a1b85cfc` before configuration.

GitHub requires a manually dispatched workflow to be available in the repository's dispatchable/default-branch workflow set. Until that workflow lands there, remote dispatch may be unavailable even though the research branch contains it. That does not block the local authoritative path.

## Host setup gate

Before measurement begins:

1. Check out `research/jar-exp-0013-runtime-acceleration` and record the exact commit.
2. Require the full runtime-acceleration test suite to pass on the real host.
3. Verify exact ToolRush and Obscura revisions against the frozen pins above.
4. Run the ToolRush read-only doctor smoke using the configured Hermes Python.
5. Verify the Obscura executable reports its version.
6. Verify the stock Hermes and Chromium baselines used for condition A.
7. Record OS/build, CPU, RAM, power state, dependency versions, Hermes revision, Chromium version, and treatment revisions.
8. Ensure no secret value is written to the evidence directory.

ToolRush activation requires a fresh isolated Hermes worker process. Do not restart a busy production gateway merely to satisfy the experiment.

Obscura's pinned CDP interface is started on loopback. Playwright clients use `connectOverCDP`, not Playwright's proprietary `connect` protocol.

## Preflight gate

Protocol revision 3 freezes:

- CPU utilization: `<= 20.0%`
- memory utilization: `<= 80.0%`
- AC power: required

Host-local configuration may not weaken or replace those values.

Before each paired timing block the executor captures the preflight snapshot. A contaminated block is recorded and excluded from treatment execution; it is not silently deleted.

## Phase 1: deterministic trace replay

The frozen trace contains identical tool and browser operations for A/B/C/D. The measurement plan contains 20 paired blocks, with each block containing A/B/C/D exactly once in the seeded randomized order.

The controlled executor records:

- trace wall-clock time;
- total tool time;
- total browser time;
- per-step timings;
- condition and paired-block identity;
- preflight snapshot;
- exact treatment pins;
- verifier result and differential correctness classification;
- execution/cleanup errors without fallback substitution.

Condition A is the block reference. B/C/D must remain semantically equivalent to A or the difference is retained as a correctness failure.

## Later confirmatory phases

### Phase 2: tool microbenchmarks

Run frozen tool operations under A and B. Record one meaningful cold sample and at least 20 warm measured samples per operation/condition pair.

### Phase 3: browser conformance and microbenchmarks

Run Chromium and Obscura against the local controlled fixture server. Record startup, navigation, DOM/evaluation, screenshot, CDP/session, redirects, storage, timeout, memory, and unsupported-feature behavior. Public-web smoke tests remain exploratory.

### Phase 4: real missions

Run identical verifier-backed missions across A/B/C/D with the same model/provider configuration for each paired block. Confirmatory promotion requires at least 100 total verified mission attempts per condition, balanced across frozen mission classes. Continue beyond the floor when needed to establish the preregistered confidence/non-inferiority bounds.

## Evidence contract

For local controlled execution, the default root is:

`C:\Aftergraph\JAR-EXP-0013\evidence`

Each Phase-1 execution receives a unique immutable id such as `phase1-<UTC timestamp>`. Under that execution directory the harness writes:

- `summary.json`
- `blocks/<pair-id>.json`
- `runs/<run-id>/metadata.json`
- `runs/<run-id>/metrics.json`
- `runs/<run-id>/stdout.log`
- `runs/<run-id>/stderr.log`
- `runs/<run-id>/verifier.json`
- `runs/<run-id>/artifacts.sha256`

The execution directory is exclusive-create. Reusing an execution id fails before treatments run. Finalized run evidence is append-only and pair/block identity is retained.

## Statistical gate

Protocol revision 3 freezes:

- 95% confidence level;
- paired percentile bootstrap for paired timing/effect measurements;
- 10,000 bootstrap resamples with seed `130013`;
- Newcombe/Wilson treatment-minus-control interval for verified mission success;
- promotion requires the lower 95% confidence bound to meet the frozen effect threshold;
- mission-success non-inferiority requires the lower treatment-minus-control bound to be `>= -0.05`.

The minimum 100 mission attempts per condition is an evidence floor, not an automatic pass. If a point estimate clears a threshold but the lower confidence bound does not, the gate remains `INCONCLUSIVE`.

## Probe states

`READY` means source pins, read-only diagnostics, path contracts, and host preflight passed. `BLOCKED` means a path, source pin, doctor/version check, or protocol contract failed. `CONTAMINATED` means the host is configured but the current load is not clean enough for confirmatory timing.

## Stop conditions

Stop the affected confirmatory block when a source pin drifts, preflight is contaminated, a treatment falls back to control behavior, a required correctness/safety contract fails, evidence cannot be persisted safely, host instability prevents comparable timing, or pair identity is lost.

## Promotion gates

After controlled-host data exists, compute the preregistered point estimates and 95% intervals, then evaluate:

- `G-TR`: ToolRush candidate
- `G-OB`: Obscura candidate
- `G-COMB`: combined candidate

Until controlled-host performance evidence exists, all three remain `INCONCLUSIVE_NO_LIVE_DATA`.
