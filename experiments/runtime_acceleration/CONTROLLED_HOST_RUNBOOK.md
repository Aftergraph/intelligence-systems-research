# JAR-EXP-0013 Controlled Windows Host Runbook

## Purpose

Execute the first authoritative JAR-EXP-0013 performance block on a real Windows Hermes host. GitHub-hosted runner timings are functional evidence only and MUST NOT be promoted as performance evidence.

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

## Local-first one-command handoff

The default authoritative readiness path is local execution on the controlled Windows host. This deliberately avoids depending on `workflow_dispatch` availability from a workflow that has not yet landed on the repository default branch.

Open elevated PowerShell in a checkout of `research/jar-exp-0013-runtime-acceleration` and run:

```powershell
Set-Location <path-to-intelligence-systems-research>
.\experiments\runtime_acceleration\start-controlled-host.ps1
```

By default the script:

1. requires Administrator privileges and Python 3.11;
2. creates an isolated harness venv under `C:\Aftergraph\JAR-EXP-0013\harness-venv`;
3. installs the research test dependencies plus `psutil` into that venv, not the Hermes application environment;
4. runs the complete `tests/runtime_acceleration` suite and stops on any failure;
5. fail-closes if the configured Hermes, ToolRush, ToolRush doctor, Obscura checkout, or Obscura executable path is missing;
6. writes the machine-local, non-secret `controlled-host.json`;
7. runs `experiments.runtime_acceleration.controlled_host` locally;
8. writes `C:\Aftergraph\JAR-EXP-0013\evidence\controlled-host-probe.json`;
9. exits non-zero unless the probe state is exactly `READY`.

The default path does **not** require GitHub CLI, does not create a runner, does not call a model/provider, and does not mutate production services.

If local paths differ, provide the corresponding PowerShell parameters explicitly. The host config MUST NOT contain credentials, provider tokens, cookies, or other secrets.

## Optional self-hosted GitHub Actions path

The repository still supports a dedicated self-hosted runner for centrally triggered reproduction. Use:

```powershell
.\experiments\runtime_acceleration\start-controlled-host.ps1 -DispatchWorkflow
```

Only this optional path requires authenticated `gh`. It obtains a short-lived repository runner registration token in memory, invokes `bootstrap-self-hosted-runner.ps1` when a dedicated runner identity is absent, and dispatches `jar-exp-0013-controlled-host.yml`.

The dedicated runner uses all four labels:

- `self-hosted`
- `Windows`
- `X64`
- `aftergraph-jar-exp-0013`

`bootstrap-self-hosted-runner.ps1` pins GitHub Actions runner `2.337.0` and verifies the Windows x64 archive against SHA256 `1150692afa94e71f872017e254ea55b6eece1eece3fe7e3a6d4c93d0a1b85cfc` before configuration.

GitHub requires a manually dispatched workflow to be available in the repository's dispatchable/default-branch workflow set. Until this workflow has landed there, remote dispatch may be unavailable even though the research branch contains the file. That limitation MUST NOT block the local authoritative probe.

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

ToolRush activation requires a fresh Hermes gateway process after the pinned treatment is installed. A new chat inside an already-running old gateway does not establish treatment activation. Do not restart a busy production gateway merely to satisfy the experiment; use a controlled experiment window.

Obscura's pinned CDP interface is started on loopback. Playwright clients must use `connectOverCDP`, not Playwright's own `connect` protocol.

## Preflight gate

Protocol revision 3 preserves the limits frozen in revision 2:

- CPU utilization: `<= 20.0%`
- memory utilization: `<= 80.0%`
- AC power: required

Host-local configuration may not weaken or replace those values.

Before each timing block capture CPU utilization, memory utilization, AC/battery state, power mode where exposed, background-process count, and thermal state where exposed. A contaminated block remains in raw evidence and MUST NOT be silently deleted.

## Statistical gate

Protocol revision 3 freezes the confirmatory statistics before the first controlled-host performance observation:

- 95% confidence level;
- paired percentile bootstrap for paired timing/effect measurements;
- 10,000 bootstrap resamples with seed `130013`;
- Newcombe/Wilson treatment-minus-control interval for verified mission success;
- promotion requires the lower 95% confidence bound to meet the frozen effect threshold;
- mission-success non-inferiority requires the lower treatment-minus-control bound to be `>= -0.05`.

The minimum 100 mission attempts per condition is an evidence floor, not an automatic statistical pass. If a point estimate clears a threshold but the lower confidence bound does not, the gate remains `INCONCLUSIVE`. If the point estimate itself is below a frozen effect threshold, the gate is `FAIL`.

## Probe states

`READY` means source pins, read-only diagnostics, path contracts, and host preflight all passed. `BLOCKED` means a path, source pin, doctor/version check, or protocol contract failed. `CONTAMINATED` means the host is correctly configured but the current load is not clean enough for a confirmatory timing block.

The probe records non-secret command metadata and host preflight state while intentionally omitting raw diagnostic stdout/stderr.

## Execution order after READY

### Phase 1: deterministic trace replay

Run the frozen trace-replay workloads first. Use at least 20 measured repetitions per trace/condition pair. Counterbalance or randomize A/B/C/D order with the recorded seed. Preserve pair identity in raw data so the preregistered paired bootstrap can resample paired blocks.

### Phase 2: tool microbenchmarks

Run the frozen tool operations under A and B. Record one meaningful cold sample and at least 20 warm measured samples per operation/condition pair.

### Phase 3: browser conformance and microbenchmarks

Run Chromium and Obscura against the local controlled fixture server. Record startup, navigation, DOM/evaluation, screenshot, CDP/session, redirects, storage, timeout and unsupported-feature behavior. Public-web smoke tests remain exploratory.

### Phase 4: real missions

Run identical verifier-backed missions across A/B/C/D with the same model/provider configuration for each paired block. Confirmatory promotion requires at least 100 total verified mission attempts per condition, balanced across frozen mission classes. Continue beyond the floor when needed to establish the preregistered confidence/non-inferiority bounds; do not weaken the confidence gate to force a verdict.

## Evidence contract

Each completed measurement run writes a unique run directory under `data/runtime_acceleration/raw/` containing:

- `metadata.json`
- `metrics.json`
- `stdout.log`
- `stderr.log`
- `verifier.json`
- `artifacts.sha256`

Raw evidence is append-only after finalization. Aggregates MUST be reproducible from raw evidence, and pair/block identity must be retained in non-secret metadata.

## Stop conditions

Stop the affected confirmatory block when a source pin drifts, preflight is contaminated, a treatment silently falls back to control behavior, a required correctness/safety contract fails, the verifier differs between comparable conditions, evidence cannot be persisted without secrets, host instability prevents comparable timing, or pair identity is lost.

## Analysis and gates

After controlled-host data exists, compute point estimates and preregistered 95% intervals, then evaluate:

- `G-TR`: ToolRush candidate
- `G-OB`: Obscura candidate
- `G-COMB`: combined candidate

Until controlled-host evidence exists, all three remain `INCONCLUSIVE_NO_LIVE_DATA`.
