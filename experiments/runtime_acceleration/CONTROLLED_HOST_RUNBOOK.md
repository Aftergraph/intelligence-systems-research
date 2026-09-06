# JAR-EXP-0013 Controlled Windows Host Runbook

## Purpose

Execute the first authoritative JAR-EXP-0013 performance block on a real Windows Hermes host. GitHub-hosted runner timings are functional evidence only and MUST NOT be promoted as performance evidence.

## Required host

Use the real Windows machine that runs Hermes and can execute the frozen Chromium, ToolRush, and Obscura treatments. The machine must remain on AC power and satisfy the preflight limits frozen in `protocol.yaml` before every confirmatory block.

## Frozen revisions

- ISR baseline: `f9fd62d57408308788822162d9ded7d9741dbb10`
- ToolRush: `4ecd8810fdc9e6e0c64af3d532f876d06f6a278e`
- Obscura: `a1e09de68c7617b8079fbb1661b0548c501971c1`

Do not silently update any treatment during the experiment. A changed source revision is a new experimental revision.

## Conditions

| Condition | Tool layer | Browser layer |
|---|---|---|
| A | Stock Hermes | Chromium |
| B | ToolRush | Chromium |
| C | Stock Hermes | Obscura |
| D | ToolRush | Obscura |

## Dedicated self-hosted runner

The controlled host is exposed to GitHub Actions only through a dedicated self-hosted runner with all four labels:

- `self-hosted`
- `Windows`
- `X64`
- `aftergraph-jar-exp-0013`

The runner must be registered for `Aftergraph/intelligence-systems-research` or an Aftergraph runner group that grants this repository access. Do not reuse the label on an unrelated machine, because that would make host identity ambiguous.

The repository includes `experiments/runtime_acceleration/bootstrap-self-hosted-runner.ps1`. It pins GitHub Actions runner `2.337.0`, verifies the Windows x64 archive against SHA256 `1150692afa94e71f872017e254ea55b6eece1eece3fe7e3a6d4c93d0a1b85cfc`, registers the dedicated label, and installs the runner as a Windows service. The registration token is read as a secure string and is never stored in the repository.

Run the bootstrap from elevated PowerShell after obtaining a short-lived repository runner registration token from GitHub:

```powershell
Set-Location <path-to-intelligence-systems-research>
.\experiments\runtime_acceleration\bootstrap-self-hosted-runner.ps1
```

Create a machine-local JSON file from `experiments/runtime_acceleration/controlled-host.example.json`, adjusting only local paths. The config MUST NOT contain credentials, provider tokens, cookies, or other secrets. The manual workflow accepts the absolute path as the `host_config_path` dispatch input, so no repository variable is required.

The workflow `.github/workflows/jar-exp-0013-controlled-host.yml` is manual-only and targets the dedicated runner. Its probe performs no provider calls and no production mutation.

## Host setup gate

1. Check out `research/jar-exp-0013-runtime-acceleration`.
2. Use Python 3.11 and install `requirements-test.txt` plus `psutil` into the runner Python environment, not the Hermes application virtual environment.
3. Run `python -m pytest tests/runtime_acceleration -q` and require zero failures.
4. Verify the exact ToolRush and Obscura revisions above.
5. Run the ToolRush read-only doctor smoke with the Hermes Python executable configured for the host.
6. Verify the Obscura executable can report its version. The planned CDP server is loopback-only at `127.0.0.1`.
7. Verify the stock Hermes and Chromium baselines used for condition A before measurement begins.
8. Record OS/build, CPU, RAM, power state, dependency versions, Hermes revision, Chromium version, and treatment revisions.
9. Ensure no secret value is written to the evidence directory.

ToolRush activation requires a fresh Hermes gateway process after the pinned treatment is installed. A new chat inside an already-running old gateway does not establish treatment activation. Do not restart a busy production gateway merely to satisfy the experiment; use the controlled experiment window.

Obscura's pinned CDP interface is started as `obscura serve --port 9222 --host 127.0.0.1`. Playwright clients must use `connectOverCDP` rather than Playwright's own `connect` protocol.

## Preflight gate

Protocol revision 3 preserves the host limits frozen in revision 2:

- CPU utilization: <=20.0%
- memory utilization: <=80.0%
- AC power: required

Host-local config may not weaken or replace those values. The bridge rejects a differing `preflight_limits` override.

Before each timing block, collect a host snapshot containing at least:

- CPU utilization
- memory utilization
- AC/battery state
- fixed power mode where exposed
- background process count
- thermal state when exposed by the platform

Classify it through `check_preflight`. A contaminated block remains in raw evidence and MUST NOT be silently deleted.

## Statistical gate

Protocol revision 3 freezes the confirmatory statistics before the first controlled-host performance observation:

- 95% confidence level;
- paired percentile bootstrap for paired timing/effect measurements;
- 10,000 bootstrap resamples with seed `130013`;
- Newcombe/Wilson treatment-minus-control interval for verified mission success;
- promotion requires the lower 95% confidence bound to meet the frozen effect threshold;
- mission-success non-inferiority requires the lower treatment-minus-control bound to be >= `-0.05`.

The minimum 100 mission attempts per condition is an evidence floor, not an automatic statistical pass. If the point estimate clears a threshold but the lower confidence bound does not, the gate remains `INCONCLUSIVE`. If the point estimate itself is below a frozen effect threshold, the gate is `FAIL`.

## Probe execution

Run the manual `JAR-EXP-0013 controlled host` workflow and provide the absolute machine-local config path in `host_config_path`. It must finish with a `READY` probe before confirmatory measurements begin. `BLOCKED` means a path, source pin, doctor/version check, or protocol contract failed. `CONTAMINATED` means the host is correctly configured but not clean enough for a confirmatory timing block.

The uploaded `controlled-host-probe.json` contains command metadata and host preflight state but intentionally omits raw command stdout/stderr to reduce secret-leak risk.

## Execution order

### Phase 1: deterministic trace replay

Run the frozen trace-replay workloads first. Use at least 20 measured repetitions per trace/condition pair. Counterbalance or randomize A/B/C/D order with the recorded seed. Preserve pair identity in raw data so the preregistered paired bootstrap can resample paired blocks rather than independent observations.

### Phase 2: tool microbenchmarks

Run the frozen tool operations under A and B. Record one meaningful cold sample and at least 20 warm measured samples per operation/condition pair.

### Phase 3: browser conformance and microbenchmarks

Run Chromium and Obscura against the local controlled fixture server. Record startup, navigation, DOM/evaluation, screenshot, CDP/session, redirects, storage, timeout and unsupported-feature behavior. Public-web smoke tests stay exploratory.

### Phase 4: real missions

Run identical verifier-backed missions across A/B/C/D with the same model/provider configuration for each paired block. Confirmatory promotion requires at least 100 total verified mission attempts per condition, balanced across frozen mission classes. Continue beyond the floor when needed to establish the preregistered confidence/non-inferiority bounds; do not weaken the confidence gate to force a verdict.

## Evidence contract

Each completed run writes a unique run directory under `data/runtime_acceleration/raw/` containing:

- `metadata.json`
- `metrics.json`
- `stdout.log`
- `stderr.log`
- `verifier.json`
- `artifacts.sha256`

Raw evidence is append-only after the run is finalized. Aggregates MUST be reproducible from raw evidence. Pair/block identity required for statistical analysis must be retained in non-secret metadata.

## Stop conditions

Stop the confirmatory run and mark the affected block when:

- a source pin drifts;
- preflight is contaminated;
- a treatment silently falls back to control behavior;
- a required correctness/safety contract fails;
- the verifier is not identical across comparable conditions;
- evidence cannot be persisted without secrets;
- host instability prevents comparable timing;
- pair identity is lost or the statistical inputs cannot be reproduced.

## Analysis and gates

After controlled-host data exists, compute point estimates and the preregistered 95% intervals, then run the promotion gate evaluator. The required gates remain:

- `G-TR`: ToolRush candidate
- `G-OB`: Obscura candidate
- `G-COMB`: combined candidate

Until controlled-host evidence exists, all three remain `INCONCLUSIVE_NO_LIVE_DATA`.

## Current implementation evidence

Hosted CI validates harness behavior and portability only. The authoritative current hosted verification head and workflow run are recorded in `data/runtime_acceleration/evidence/readiness.json`. Neither hosted CI nor this runbook is controlled-host performance evidence.
