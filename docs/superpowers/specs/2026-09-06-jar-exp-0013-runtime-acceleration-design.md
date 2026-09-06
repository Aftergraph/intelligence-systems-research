# JAR-EXP-0013 — Agent Runtime Acceleration Design

**Repository:** `Aftergraph/intelligence-systems-research`  
**Target branch:** `research/jar-exp-0013-runtime-acceleration`  
**Target path:** `docs/superpowers/specs/2026-09-06-jar-exp-0013-runtime-acceleration-design.md`  
**Experiment ID:** `JAR-EXP-0013`  
**Date:** 2026-09-06  
**Status:** DESIGN APPROVED; IMPLEMENTATION NOT STARTED  
**Principal researcher:** Jonas Abde

## 1. Purpose

Evaluate whether ToolRush and Obscura materially improve the performance and resource efficiency of real Hermes-style agent workloads without reducing correctness, safety, compatibility, or verified mission success.

The study is deliberately evidence-first. Upstream benchmark claims are treated as hypotheses to reproduce, not as accepted Aftergraph platform claims. No result from this experiment may automatically change WORKS, Trust Gateway, AIE, or any production runtime.

## 2. Repository and ownership boundary

The experiment belongs in `Aftergraph/intelligence-systems-research` because that repository owns Labs / Evals / Assurance and reproducible research evidence.

The experiment MUST NOT modify production runtime behavior in:

- `Aftergraph/works-execution`
- `Aftergraph/trust-gateway`
- `Aftergraph/aie`
- governance contracts in `Aftergraph/after-graph-governance`

Promotion from research to production requires a separate architecture decision and implementation cycle after this experiment reaches its evidence gates.

## 3. Immutable source pins

The first preregistered run must use exact source revisions, not floating branches.

| Component | Repository | Pinned revision |
|---|---|---|
| ISR baseline | `Aftergraph/intelligence-systems-research` | `f9fd62d57408308788822162d9ded7d9741dbb10` |
| ToolRush | `OnlyTerp/toolrush` | `4ecd8810fdc9e6e0c64af3d532f876d06f6a278e` |
| Obscura | `h4ckf0r0day/obscura` | `a1e09de68c7617b8079fbb1661b0548c501971c1` |

If any source revision changes, that constitutes a new experimental revision and must be recorded separately. Results from different source revisions must not be silently pooled.

## 4. Research questions

### RQ1 — Tool transport

Does ToolRush reduce local tool-operation overhead and end-to-end mission wall-clock time relative to stock Hermes tooling while preserving identical observable results and safety behavior?

### RQ2 — Browser runtime

Does Obscura reduce browser startup cost, memory use, and browser-operation latency relative to Chromium while retaining sufficient browser compatibility for agent workflows?

### RQ3 — Combined system

Do ToolRush and Obscura compose into an end-to-end improvement greater than either intervention alone without introducing a correctness, safety, reliability, or compatibility regression?

### RQ4 — Practical value

Are any measured improvements large enough at mission level to justify additional runtime complexity and maintenance burden?

## 5. Experimental design

Use a 2 × 2 factorial design with four conditions.

| Condition | Tool layer | Browser layer |
|---|---|---|
| A — CONTROL | Stock Hermes | Chromium |
| B — TOOLRUSH | ToolRush enabled | Chromium |
| C — OBSCURA | Stock Hermes | Obscura |
| D — COMBINED | ToolRush enabled | Obscura |

Every comparable run uses the same:

- workload definition;
- repository snapshot;
- model and provider configuration;
- prompt and mission contract;
- verifier;
- machine power policy;
- environment variables unrelated to the treatment;
- network conditions to the extent controllable;
- warm/cold classification;
- repetition policy.

Run order must be randomized or counterbalanced within blocks so condition ordering does not systematically favor one treatment.

## 6. Hypotheses

### H1 — ToolRush

ToolRush lowers aggregate local tool overhead by at least 30% and lowers wall-clock time of tool-heavy verified missions by at least 10%, with no new correctness or safety failures.

### H2 — Obscura

Obscura lowers peak browser RSS by at least 40% and cold browser startup time by at least 20%, while passing at least 95% of the preregistered browser compatibility surface and causing no material verified-success regression.

### H3 — Combined

The combined ToolRush + Obscura condition lowers end-to-end mission wall-clock time by at least 15% relative to control while remaining non-inferior on verified mission outcomes.

### Null conditions

A treatment is not considered useful when its measured benefit is below its preregistered threshold, when uncertainty includes a practically null effect, or when correctness/safety/compatibility gates fail.

## 7. Workload strata

### 7.1 Tool microbenchmarks

Measure isolated operations under stock and ToolRush paths:

- bounded source-file read;
- large-file paginated read;
- exact content search;
- repository content search;
- context search;
- no-match search;
- file discovery;
- warm shell builtin;
- Python process launch;
- Git process launch;
- sequential read RPC;
- parallel read RPC;
- mixed read/search RPC.

Microbenchmarks are diagnostic only. They cannot establish mission-level usefulness.

### 7.2 Browser microbenchmarks

Primary browser timing runs use a local controlled fixture server so DNS, CDN, remote rate limits, and public-network variance do not dominate browser-engine measurements. Public-web smoke tests are exploratory and are reported separately.

Measure Chromium and Obscura for:

- cold process startup;
- warm process reuse;
- first navigation;
- repeated navigation;
- DOM query;
- JavaScript evaluation;
- screenshot;
- PDF export where supported by both paths;
- CDP session establishment;
- cookie/session persistence;
- redirects;
- basic form interaction;
- dynamic JavaScript pages;
- failure and timeout handling.

### 7.3 Browser compatibility suite

The compatibility suite must compare semantic outcomes rather than assuming API compatibility equals behavioral compatibility. It covers:

- navigation result and final URL;
- DOM text and selected attributes;
- JavaScript execution results;
- cookies and local storage where supported;
- request redirects;
- screenshots being produced and non-empty;
- Playwright/Puppeteer connection compatibility where part of the tested interface;
- deterministic failures for unsupported features;
- cancellation and timeout behavior.

No anti-bot or CAPTCHA-bypass claim is part of this study.

### 7.4 Deterministic trace-replay missions

Before introducing model stochasticity, replay fixed action traces through each compatible treatment. A trace contains an ordered set of file reads, searches, shell commands, browser navigations, DOM queries, and verifier checks. The trace payload, inputs, and expected outputs are frozen before execution. Trace replay isolates runtime transport effects from model behavior.

Trace-replay results are required for causal attribution of runtime latency and correctness. They do not replace full agent missions.

### 7.5 Real agent missions

Use a fixed, preregistered mission set with independently verifiable outcomes. Mission classes:

1. **Repository inspection** — inspect code, locate relevant files, produce a verifier-checked answer.
2. **Code-search-heavy mission** — repeated search/read operations with deterministic target findings.
3. **Read-heavy mission** — inspect multiple source files and assemble a verifier-checked artifact.
4. **Browser research mission** — navigate a controlled test site, extract specified facts, produce evidence.
5. **Mixed mission** — combine repository work, shell execution, browser work, and final verification.

The same model/provider must be used across A/B/C/D for a given block.

## 8. Measurements

### Primary metrics

- `verified_mission_success_rate`
- `mission_wall_clock_ms`
- `tool_time_total_ms`
- `browser_time_total_ms`
- `peak_rss_mb`
- `correctness_delta`

### Secondary metrics

- `tool_latency_p50_ms`
- `tool_latency_p95_ms`
- `browser_startup_cold_ms`
- `browser_startup_warm_ms`
- `cpu_time_ms`
- `process_count_peak`
- `tool_calls`
- `browser_operations`
- `fallback_count`
- `timeout_count`
- `error_count`
- `model_input_tokens`
- `model_output_tokens`
- `provider_cost_usd`
- `mission_cost_usd`

### Derived metrics

- percentage change versus control;
- treatment main effect for ToolRush;
- treatment main effect for Obscura;
- ToolRush × Obscura interaction effect;
- cost per verified outcome;
- latency per verified outcome;
- memory per successful browser mission.

## 9. Correctness and safety contracts

Performance evidence is invalid for promotion if a treatment violates any required contract.

### ToolRush differential contract

For operations that claim compatible acceleration:

- content results must match stock semantics;
- error class must match or be explicitly classified as a known compatible deviation;
- access guards remain active;
- write-capable operations are not admitted into read-only parallel execution;
- tool-call budgets remain enforced;
- cancellation must not cause command replay;
- unsupported accelerated cases fall back to the stock path.

### Browser differential contract

For required browser features:

- semantically relevant page outputs match;
- unsupported features fail explicitly rather than silently fabricating success;
- treatment-specific errors are recorded;
- browser substitution must not upgrade a failed mission to VERIFIED without the same independent verifier used by control.

## 10. Negative controls

At minimum, implement controls that are expected to fail when the tested mechanism is deliberately disabled or broken:

1. ToolRush native-read lane disabled.
2. ToolRush direct-search lane disabled.
3. Parallel read execution serialized.
4. Unsafe scheduler admission deliberately restored in an isolated test fixture.
5. Obscura provider deliberately returns a mismatched DOM result.
6. Browser compatibility adapter deliberately suppresses an unsupported-feature error.

A negative control counts only when it fails for the intended assertion.

## 11. Repetition and timing protocol

### Microbenchmarks

For each microbenchmark/condition pair:

- execute one recorded cold sample where meaningful;
- execute at least 20 warm measured repetitions;
- report median, p95, min, max, and raw samples;
- do not delete outliers merely because they are inconvenient;
- classify environmental interruptions rather than silently removing them.

### Mission benchmarks

For exploratory development, each mission/condition pair may use 10 measured repetitions. A confirmatory mission-level PASS requires at least **100 total verified mission attempts per condition**, balanced across the frozen mission classes. If provider cost prevents reaching this floor, mission-level efficacy remains `INCONCLUSIVE` rather than being promoted from a smaller sample.

For deterministic trace-replay workloads, use at least 20 measured repetitions per trace/condition pair. For stochastic model missions, run order is randomized within paired blocks and the randomization seed is recorded before execution.

## 12. Environment capture

Before each performance block, the controlled host records a preflight snapshot: AC/battery state, fixed power mode, CPU utilization, memory pressure, background-process count, and thermal state when the platform exposes it. A block is marked environmentally contaminated when the preregistered preflight limits are exceeded; contaminated blocks remain in raw evidence but are excluded from confirmatory timing summaries by an explicit rule recorded before data collection.

Every evidence bundle records:

- operating system and build;
- CPU model and logical-core count;
- RAM;
- storage type when available;
- Python version;
- Rust toolchain version;
- Node.js version if used;
- Hermes version / exact revision;
- ToolRush exact revision;
- Obscura exact revision;
- Chromium exact version;
- Playwright/Puppeteer versions if used;
- model and provider identifier;
- relevant dependency lock hashes;
- machine power mode;
- execution timestamp;
- experiment revision;
- git working-tree cleanliness.

Secret values must never be persisted in evidence.

## 13. Evidence format

Raw evidence is append-only for a completed run. Each run receives a unique `run_id` and writes:

```text
metadata.json
metrics.json
stdout.log
stderr.log
verifier.json
artifacts.sha256
```

Aggregated analysis must be derivable entirely from raw evidence. Generated summaries never replace raw measurements.

## 14. Planned repository structure

```text
experiments/
└── runtime_acceleration/
    ├── README.md
    ├── protocol.yaml
    ├── preregistration.md
    ├── environment.py
    ├── workloads/
    │   ├── tool_microbench.yaml
    │   ├── browser_compat.yaml
    │   ├── coding_missions.yaml
    │   └── mixed_agent_missions.yaml
    ├── adapters/
    │   ├── stock_hermes.py
    │   ├── toolrush.py
    │   ├── chromium.py
    │   └── obscura.py
    ├── runners/
    │   ├── microbench.py
    │   ├── browser_bench.py
    │   ├── mission_bench.py
    │   └── factorial.py
    ├── verification/
    │   ├── differential.py
    │   ├── browser_conformance.py
    │   └── negative_controls.py
    └── analysis/
        ├── analyze.py
        └── report.py

data/
└── runtime_acceleration/
    ├── manifests/
    ├── raw/
    ├── processed/
    └── evidence/

tests/
└── runtime_acceleration/

JAR-EXP-0013-RUNTIME-ACCELERATION.md
```

The experiment also adds one immutable registry entry to `data/experiment_registry.csv` using ID `JAR-EXP-0013`.

## 15. CI and execution environments

### Primary performance evidence

Primary performance evidence comes from a controlled real Windows Hermes host. GitHub-hosted runner timings must not be used as the main performance claim because runner hardware and co-tenancy are uncontrolled.

### CI reproducibility

GitHub Actions should run:

- Windows functional and compatibility tests;
- Linux Obscura portability and browser-conformance tests where supported;
- schema/config validation;
- deterministic unit tests;
- negative controls that are safe for CI;
- analysis validation on checked-in fixture evidence.

## 16. Statistical analysis

For every primary timing/resource metric:

- retain all raw samples;
- report medians and p95s;
- report percentage difference from control;
- compute bootstrap confidence intervals for median differences;
- report per-workload results before any pooled summary;
- treat workload as a blocking factor in factorial analysis;
- report main effects and interaction effect separately;
- distinguish exploratory findings from preregistered confirmatory outcomes.

Verified mission success is reported as count/total and proportion with a 95% Wilson interval. For confirmatory treatment-vs-control comparison, the preregistered non-inferiority margin is **5 percentage points absolute**. A treatment may pass the mission-success gate only when the confidence interval for the treatment-minus-control difference does not extend below `-0.05`. Deterministic compatibility and trace-replay workloads additionally require zero new treatment-induced correctness failures. A faster condition with worse verified success beyond this margin is a failed treatment.

## 17. Promotion gates

### G-TR — ToolRush candidate

PASS only when all are true:

- aggregate local tool overhead improves by at least 30%;
- tool-heavy mission wall-clock improves by at least 10%;
- no new correctness failure;
- no safety-boundary regression;
- fallbacks are explicit and measured.

### G-OB — Obscura candidate

PASS only when all are true:

- peak browser RSS improves by at least 40%;
- cold startup improves by at least 20%;
- at least 95% of required compatibility cases pass;
- verified mission success satisfies the 5-percentage-point non-inferiority rule in Section 16;
- unsupported behavior fails explicitly.

### G-COMB — Combined candidate

PASS only when all are true:

- end-to-end mission wall-clock improves by at least 15%;
- verified mission success satisfies the 5-percentage-point non-inferiority rule in Section 16;
- combined treatment introduces no new correctness or safety failure;
- combined maintenance complexity is justified by mission-level benefit.

A failed gate remains a valid negative research result. No threshold may be lowered after data collection to manufacture a PASS.

## 18. Rollback and isolation

Experiment activation must be reversible without editing upstream source trees in place.

- ToolRush treatment is enabled only in the experimental environment and must support its own kill switch / disabled control path.
- Obscura is introduced through an experimental adapter, not as the default production browser.
- Control condition remains executable throughout the study.
- No production gateway restart is part of the research implementation.
- No production configuration is changed by the benchmark harness.

## 19. Falsification conditions

The experiment falsifies its practical acceleration thesis if any of the following holds:

- microbenchmark wins do not translate to material mission-level improvements;
- correctness differs from the control in required operations;
- safety gates are weakened;
- browser compatibility is below the preregistered threshold;
- memory/latency wins are offset by material reliability loss;
- combined mode is not meaningfully better than the simpler individual treatment;
- maintenance/update burden outweighs measured mission-level benefit.

## 20. Deliverables

The experiment is complete only when the repository contains:

1. preregistration and machine-readable protocol;
2. pinned-source manifest;
3. reproducible environment capture;
4. deterministic test suite;
5. differential correctness suite;
6. browser compatibility suite;
7. negative controls;
8. microbenchmark runner;
9. mission benchmark runner;
10. raw evidence from the controlled host;
11. analysis scripts;
12. machine-readable results;
13. human-readable final report;
14. registry update for `JAR-EXP-0013`;
15. explicit PASS/FAIL verdict for G-TR, G-OB, and G-COMB.

## 21. Non-goals

This experiment does not:

- claim that headless Chrome is obsolete;
- claim that Obscura bypasses bot detection, CAPTCHA, or access controls;
- modify AIE normative standards;
- integrate a treatment into production WORKS or Trust Gateway;
- measure model-quality improvements;
- optimize provider/network latency;
- introduce a new browser framework when an adapter suffices;
- treat GitHub Actions latency as authoritative performance evidence.

## 22. Implementation gate

This document defines the approved design only. Implementation begins only after this written specification has been reviewed, after which a separate implementation plan is created under `docs/superpowers/plans/` and executed task-by-task with test-driven development and independent verification.
