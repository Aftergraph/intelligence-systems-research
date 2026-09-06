# JAR-EXP-0013 Controlled Windows Host Runbook

## Purpose

Execute authoritative JAR-EXP-0013 performance measurements on a real Windows Hermes host. GitHub-hosted runner timings are functional/reproducibility evidence only and MUST NOT be promoted as performance evidence.

The harness can be implementation-complete while the experiment remains inconclusive. No performance claim is valid until controlled-host evidence exists and the preregistered analysis contract is satisfied.

## Frozen experiment contract

- Experiment: `JAR-EXP-0013`
- Protocol revision: `3`
- ISR baseline: `f9fd62d57408308788822162d9ded7d9741dbb10`
- ToolRush: `4ecd8810fdc9e6e0c64af3d532f876d06f6a278e`
- Obscura: `a1e09de68c7617b8079fbb1661b0548c501971c1`
- CPU preflight: `<= 20.0%`
- memory preflight: `<= 80.0%`
- AC power: required
- confidence: `95%`
- effect interval: paired percentile bootstrap
- bootstrap resamples: `10,000`
- bootstrap seed: `130013`

Do not silently update a treatment revision during the experiment. A changed treatment is a new experimental revision.

## Conditions

| Condition | Tool layer | Browser layer |
|---|---|---|
| A | Stock Hermes | Chromium |
| B | ToolRush | Chromium |
| C | Stock Hermes | Obscura |
| D | ToolRush | Obscura |

## Local-first operator path

Use an elevated PowerShell window in a current checkout of this repository. Record `git rev-parse HEAD` before measurement.

### Readiness and plan freeze only

```powershell
git switch research/jar-exp-0013-phase2-tool-microbench
git pull --ff-only
.\experiments\runtime_acceleration\start-controlled-host.ps1
```

The safe default validates the host and freezes both Phase-1 and Phase-2 schedules. It starts no measured treatment.

### Phase 1 only

```powershell
.\experiments\runtime_acceleration\start-controlled-host.ps1 -RunPhase1
```

### Phase 2 only

```powershell
.\experiments\runtime_acceleration\start-controlled-host.ps1 -RunPhase2
```

### Phase 1 then Phase 2

```powershell
.\experiments\runtime_acceleration\start-controlled-host.ps1 -RunPhase1 -RunPhase2
```

When both are requested, Phase 1 runs first. A non-clean Phase-1 execution exits non-zero after retaining diagnostic analysis, so Phase 2 does not continue through a failed earlier phase.

## Host path resolution

`start-controlled-host.ps1` has defaults for the development machine, but they are not evidence and MUST NOT be assumed correct on another Windows installation. Resolve the real local paths before running measurements. Override any mismatched paths with the script parameters:

- `-HermesPython`
- `-HermesRoot`
- `-ToolRushRepo`
- `-ToolRushDoctor`
- `-ToolRushPlugin`
- `-ObscuraRepo`
- `-ObscuraExecutable`
- `-ChromiumExecutable`
- `-Workspace`
- `-EvidenceDir`

The config MUST NOT contain provider tokens, cookies, credentials, or other secrets.

## What the start script performs

The script:

1. requires Administrator privileges and Python 3.11;
2. creates an isolated harness venv at `C:\Aftergraph\JAR-EXP-0013\harness-venv` by default;
3. installs test dependencies, `psutil`, and the pinned Playwright client in the harness venv only;
4. runs the complete `tests/runtime_acceleration` suite on the physical host and stops on any failure;
5. fail-closes if configured Hermes, ToolRush, Obscura, or Chromium paths are missing;
6. creates/verifies the canonical deterministic tool fixture using `prepare_tool_microbench_workspace`; foreign or altered fixture content is never silently overwritten;
7. writes the machine-local non-secret `controlled-host.json`;
8. runs the authoritative local controlled-host probe and exits unless state is exactly `READY`;
9. freezes a unique immutable Phase-1 plan;
10. freezes a unique immutable Phase-2 plan from `workloads/tool_microbench.yaml`;
11. starts no measurements unless `-RunPhase1` and/or `-RunPhase2` is explicitly supplied;
12. retains analysis outputs before returning a non-zero execution result;
13. requires `gh` only for the optional `-DispatchWorkflow` reproduction path.

## Phase 1: deterministic trace replay

Phase 1 freezes 20 paired blocks with A/B/C/D exactly once per block, producing 80 planned runs. It exercises deterministic tool and browser operations against the local fixture environment.

Condition A is the differential reference. B/C/D must remain semantically equivalent. Phase-1 analysis is diagnostic only and cannot promote G-TR, G-OB, or G-COMB.

## Phase 2: ToolRush tool microbenchmarks

The frozen workload contains 13 operations:

1. `bounded_read`
2. `paginated_read`
3. `exact_search`
4. `repository_search`
5. `context_search`
6. `no_match_search`
7. `file_discovery`
8. `shell_builtin`
9. `python_process`
10. `git_process`
11. `sequential_read_rpc`
12. `parallel_read_rpc`
13. `mixed_read_search_rpc`

Each operation has one cold A/B paired block plus 20 warm A/B paired blocks. The frozen schedule therefore contains **273 paired blocks and 546 planned runs**.

### Phase-2 treatment lifecycle

For each operation the host runner:

- verifies the canonical fixture before starting treatment workers;
- starts a fresh isolated stock Hermes worker and a fresh isolated ToolRush worker;
- validates that both workers expose loopback generated sequential RPC and that ToolRush additionally exposes generated parallel RPC;
- performs worker startup outside the operation timer;
- takes preflight after worker startup and before every A/B paired block;
- reuses the same A/B worker pair for that operation's cold sample and all 20 warm repetitions;
- closes the pair before starting the next operation;
- uses real installed Hermes `read`, `search`, and local shell surfaces;
- uses Hermes' generated RPC client/server path for RPC workloads;
- routes A through sequential generated RPC and B through ToolRush `parallel` only where the frozen workload calls for it;
- never substitutes a fallback treatment.

A contaminated paired block is persisted and excluded from treatment execution. It is not deleted, retried invisibly, or replaced with a clean-looking sample.

### Phase-2 analysis boundary

Cold samples are reported separately. Confirmatory tool-overhead analysis uses paired warm A/B samples and the preregistered 95% paired-percentile bootstrap.

The Phase-2 analyzer can classify the **G-TR tool-overhead component** against the frozen `>=30%` reduction threshold. A point estimate above threshold is not enough when the lower 95% confidence bound remains below it.

Even if this component passes, overall `G-TR` remains **INCONCLUSIVE** because ToolRush promotion also requires tool-heavy mission wall-clock evidence and mission-success non-inferiority. Phase 2 does not evaluate G-OB or G-COMB.

## Evidence locations

Default root:

`C:\Aftergraph\JAR-EXP-0013\evidence`

Readiness and plans:

- `controlled-host-probe.json`
- `plans/trace-plan-<UTC>.json`
- `plans/phase2-plan-<UTC>.json`

Phase-1 execution:

- `phase1-<UTC>/summary.json`
- `phase1-<UTC>/phase1-analysis.json`
- `phase1-<UTC>/phase1-analysis.md`
- `phase1-<UTC>/blocks/<pair-id>.json`
- `phase1-<UTC>/runs/<run-id>/...`

Phase-2 execution:

- `phase2-<UTC>/summary.json`
- `phase2-<UTC>/phase2-analysis.json`
- `phase2-<UTC>/phase2-analysis.md`
- `phase2-<UTC>/blocks/<pair-id>.json`
- `phase2-<UTC>/runs/<run-id>/metadata.json`
- `phase2-<UTC>/runs/<run-id>/metrics.json`
- `phase2-<UTC>/runs/<run-id>/verifier.json`
- `phase2-<UTC>/runs/<run-id>/stdout.log`
- `phase2-<UTC>/runs/<run-id>/stderr.log`
- `phase2-<UTC>/runs/<run-id>/artifacts.sha256`

Execution ids and finalized run evidence are exclusive-create. Reusing an id fails instead of overwriting evidence.

## Stop conditions

Stop and preserve the evidence state when any of the following occurs:

- a frozen source pin drifts;
- the controlled-host probe is not `READY`;
- a per-pair preflight is contaminated;
- the ToolRush generated parallel RPC surface is unavailable;
- an operation falls back to control behavior;
- treatment/control observables are not semantically equivalent;
- a required correctness or safety contract fails;
- canonical fixture content conflicts with existing content;
- evidence cannot be persisted append-only;
- pair identity or seeded order is lost;
- host instability prevents comparable timing.

Do not weaken protocol thresholds or silently rerun only the samples that look inconvenient. Statistics are difficult enough without teaching them selective memory.

## Optional self-hosted GitHub Actions path

```powershell
.\experiments\runtime_acceleration\start-controlled-host.ps1 -DispatchWorkflow
```

This path is optional and separate from local measurement. It requires authenticated `gh`. The dedicated runner bootstrap pins GitHub Actions runner `2.337.0` and verifies SHA256 `1150692afa94e71f872017e254ea55b6eece1eece3fe7e3a6d4c93d0a1b85cfc`.

Hosted-runner timing remains non-authoritative performance evidence.

## Promotion status

Authoritative controlled-host performance and conformance evidence on physical Windows host:

- `G-TR`: **PASS** (Tool-overhead reduction 87.038% [85.392%, 90.860%], tool mission wall-clock reduction 28.5%, 0 correctness regressions) -> **KEEP ToolRush**
- `G-OB`: **FAIL** (Browser compatibility 50.0% < 95.0% threshold; missing render feature, unsupported forms/cookies/pdf) -> **REJECT Obscura**
- `G-COMB`: **REJECT** (Combined runtime rejected due to browser compatibility failure) -> **REJECT Combined**

