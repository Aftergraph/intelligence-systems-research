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

## Host setup gate

1. Check out `research/jar-exp-0013-runtime-acceleration`.
2. Use Python 3.11 and install `requirements-test.txt`.
3. Run `python -m pytest tests/runtime_acceleration -q` and require zero failures.
4. Verify the exact ToolRush and Obscura revisions above.
5. Verify the stock Hermes and Chromium baselines used for condition A.
6. Record OS/build, CPU, RAM, power state, dependency versions, Hermes revision, Chromium version, and treatment revisions.
7. Ensure no secret value is written to the evidence directory.

## Preflight gate

Before each timing block, collect a host snapshot containing at least:

- CPU utilization
- memory utilization
- AC/battery state
- fixed power mode
- background process count
- thermal state when exposed by the platform

Classify it with the frozen limits in `protocol.yaml` through `check_preflight`. A contaminated block remains in raw evidence and MUST NOT be silently deleted.

## Execution order

### Phase 1: deterministic trace replay

Run the frozen trace-replay workloads first. Use at least 20 measured repetitions per trace/condition pair. Counterbalance or randomize A/B/C/D order with the recorded seed.

### Phase 2: tool microbenchmarks

Run the frozen tool operations under A and B. Record one meaningful cold sample and at least 20 warm measured samples per operation/condition pair.

### Phase 3: browser conformance and microbenchmarks

Run Chromium and Obscura against the local controlled fixture server. Record startup, navigation, DOM/evaluation, screenshot, CDP/session, redirects, storage, timeout and unsupported-feature behavior. Public-web smoke tests stay exploratory.

### Phase 4: real missions

Run identical verifier-backed missions across A/B/C/D with the same model/provider configuration for each paired block. Confirmatory promotion requires at least 100 total verified mission attempts per condition, balanced across frozen mission classes.

## Evidence contract

Each completed run writes a unique run directory under `data/runtime_acceleration/raw/` containing:

- `metadata.json`
- `metrics.json`
- `stdout.log`
- `stderr.log`
- `verifier.json`
- `artifacts.sha256`

Raw evidence is append-only after the run is finalized. Aggregates MUST be reproducible from raw evidence.

## Stop conditions

Stop the confirmatory run and mark the affected block when:

- a source pin drifts;
- preflight is contaminated;
- a treatment silently falls back to control behavior;
- a required correctness/safety contract fails;
- the verifier is not identical across comparable conditions;
- evidence cannot be persisted without secrets;
- host instability prevents comparable timing.

## Analysis and gates

After controlled-host data exists, run the registered analysis and promotion gate evaluator. The required gates remain:

- `G-TR`: ToolRush candidate
- `G-OB`: Obscura candidate
- `G-COMB`: combined candidate

Until controlled-host evidence exists, all three remain `INCONCLUSIVE_NO_LIVE_DATA`.
