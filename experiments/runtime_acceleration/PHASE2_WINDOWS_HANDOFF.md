# JAR-EXP-0013 Phase-2 Windows Handoff

## Mission

Run the completed Phase-2 ToolRush-vs-stock Hermes microbenchmark harness on the real controlled Windows host and return evidence. Do not redesign the experiment, update treatment revisions, relax preflight thresholds, or infer performance from hosted CI.

Repository: `Aftergraph/intelligence-systems-research`

Branch: `research/jar-exp-0013-phase2-tool-microbench`

Validated implementation head before handoff documentation: `6745356e30c4ef0240f37f42d054d85f3a2c782b`

PR: `#8`

## Frozen treatment identity

- ToolRush: `4ecd8810fdc9e6e0c64af3d532f876d06f6a278e`
- Obscura: `a1e09de68c7617b8079fbb1661b0548c501971c1`
- protocol revision: `3`
- CPU preflight: `<=20%`
- memory preflight: `<=80%`
- AC power: required
- warm repetitions per operation: `20`
- bootstrap seed: `130013`

**Do not run `hermes update` before the measurement.** Capture the exact currently installed Hermes revision/build instead. Updating Hermes immediately before treatment would change the runtime under test and contaminate the comparison.

## Phase-2 schedule

The frozen workload has 13 operations. Each operation receives one cold A/B pair and 20 warm A/B pairs.

- paired blocks: `273`
- planned runs: `546`
- A: stock Hermes
- B: ToolRush
- fresh isolated A/B worker pair per operation
- same worker pair reused through that operation's cold + warm samples
- worker startup outside the measured operation timer
- preflight after worker startup and before every A/B block
- real Hermes read/search/shell surfaces
- real Hermes generated RPC path
- ToolRush generated parallel RPC only where the frozen workload requests it
- no fallback

## Step 1: inspect, do not mutate

In elevated PowerShell, locate the existing ISR checkout and inspect the current host:

```powershell
where.exe hermes
(Get-Command hermes -ErrorAction Stop).Source
hermes --version
```

Locate the real Hermes root/Python, installed ToolRush plugin/doctor, ToolRush checkout, Obscura checkout/executable, and Chromium executable. Do not assume the defaults in the script are correct for this machine.

Capture these before measurement:

```powershell
git -C <HERMES_ROOT> rev-parse HEAD
git -C <TOOLRUSH_REPO> rev-parse HEAD
git -C <OBSCURA_REPO> rev-parse HEAD
```

The ToolRush checkout MUST equal the frozen pin. The controlled-host probe also requires the installed ToolRush `__init__.py` and `doctor.py` to byte-match `v2/plugin/__init__.py` and `v2/plugin/doctor.py` from that pinned checkout. If they differ, repair the installation from the pinned checkout, then start a fresh Hermes process. Do not substitute a newer ToolRush revision.

## Step 2: update only the ISR experiment branch

```powershell
Set-Location <ISR_CHECKOUT>
git fetch origin
git switch research/jar-exp-0013-phase2-tool-microbench
git pull --ff-only
git status --short
git rev-parse HEAD
```

Stop if the ISR checkout has unrelated uncommitted changes. Do not clean or reset another agent's work.

## Step 3: readiness-only pass

Run the safe default first with explicit local paths when they differ from defaults:

```powershell
.\experiments\runtime_acceleration\start-controlled-host.ps1 `
  -HermesPython <HERMES_PYTHON> `
  -HermesRoot <HERMES_ROOT> `
  -ToolRushRepo <TOOLRUSH_REPO> `
  -ToolRushDoctor <INSTALLED_TOOLRUSH_DOCTOR> `
  -ToolRushPlugin <INSTALLED_TOOLRUSH_PLUGIN> `
  -ObscuraRepo <OBSCURA_REPO> `
  -ObscuraExecutable <OBSCURA_EXE> `
  -ChromiumExecutable <CHROMIUM_EXE>
```

This must:

1. run the local JAR-EXP-0013 test suite;
2. prepare/verify the canonical deterministic fixture;
3. verify ToolRush and Obscura pins;
4. verify the installed ToolRush plugin + doctor match the pinned checkout;
5. run ToolRush doctor smoke;
6. produce `controlled-host-probe.json` with state exactly `READY`;
7. freeze unique Phase-1 and Phase-2 plans;
8. start no measurements.

Do not continue if the probe is `BLOCKED` or `CONTAMINATED`.

## Step 4: execute Phase 2

After a READY pass, rerun with `-RunPhase2` and the same explicit paths:

```powershell
.\experiments\runtime_acceleration\start-controlled-host.ps1 `
  -RunPhase2 `
  -HermesPython <HERMES_PYTHON> `
  -HermesRoot <HERMES_ROOT> `
  -ToolRushRepo <TOOLRUSH_REPO> `
  -ToolRushDoctor <INSTALLED_TOOLRUSH_DOCTOR> `
  -ToolRushPlugin <INSTALLED_TOOLRUSH_PLUGIN> `
  -ObscuraRepo <OBSCURA_REPO> `
  -ObscuraExecutable <OBSCURA_EXE> `
  -ChromiumExecutable <CHROMIUM_EXE>
```

The run writes immutable evidence under `C:\Aftergraph\JAR-EXP-0013\evidence` by default.

Expected files:

```text
controlled-host-probe.json
plans\phase2-plan-<UTC>.json
phase2-<UTC>\summary.json
phase2-<UTC>\phase2-analysis.json
phase2-<UTC>\phase2-analysis.md
phase2-<UTC>\blocks\...
phase2-<UTC>\runs\...
```

## Stop conditions

Stop, preserve evidence, and report the exact failure when any of these occurs:

- ToolRush or Obscura pin mismatch;
- installed ToolRush plugin/doctor differs from the pinned checkout;
- local test suite failure;
- controlled-host state is not `READY`;
- generated sequential/parallel RPC surface is missing;
- canonical fixture collision;
- a paired-block preflight is contaminated;
- A/B correctness differs;
- any fallback is attempted;
- append-only evidence write fails;
- host instability prevents comparable measurement.

Do not delete contaminated blocks. Do not rerun only inconvenient samples. Do not lower thresholds.

## Required return report

Return a concise report with:

```text
ISR_HEAD=<sha>
HERMES_HEAD=<sha or explicit non-git build identity>
TOOLRUSH_HEAD=<sha>
OBSCURA_HEAD=<sha>
PROBE_STATE=<READY|BLOCKED|CONTAMINATED>
PHASE2_STATE=<state or NOT_RUN>
PLANNED_PAIRS=273
CLEAN_PAIRS=<n>
CONTAMINATED_PAIRS=<n>
COMPLETED_RUNS=<n>
CORRECTNESS_FAILURES=<n>
G_TR_TOOL_OVERHEAD_COMPONENT=<PASS|FAIL|INCONCLUSIVE|NOT_RUN>
OBSERVED_WARM_REDUCTION=<value if available>
CI95=<low..high if available>
SUMMARY_PATH=<path>
ANALYSIS_JSON_PATH=<path>
ANALYSIS_MD_PATH=<path>
```

Attach or make available the probe, frozen Phase-2 plan, Phase-2 summary, and Phase-2 analysis outputs.

## Interpretation boundary

A Phase-2 component PASS does **not** mean G-TR passes. Full G-TR still requires the preregistered tool-heavy mission wall-clock effect and mission-success non-inferiority. G-OB and G-COMB are not promoted by Phase 2.

Until real controlled-host evidence exists, all performance gates remain `INCONCLUSIVE_NO_LIVE_DATA`.
