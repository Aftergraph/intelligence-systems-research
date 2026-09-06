# JAR-EXP-0013 Runtime Acceleration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a preregistered, verifier-backed 2×2 evaluation harness that measures ToolRush and Obscura independently and together against stock Hermes + Chromium without changing production runtimes.

**Architecture:** The experiment is an isolated Python package under `experiments/runtime_acceleration/` with frozen machine-readable protocol, adapters, deterministic trace replay, differential verification, benchmark runners, append-only evidence, and analysis. Treatments are selected through adapters and explicit config; control remains runnable at every stage. Performance claims are produced only from raw evidence and promotion gates defined in the approved spec.

**Tech Stack:** Python 3.11+, pytest, PyYAML, stdlib `statistics`/`subprocess`/`json`/`hashlib`, optional psutil for host metrics, Chromium/Playwright and Obscura only on hosts where installed, GitHub Actions for functional reproducibility.

**Spec:** `docs/superpowers/specs/2026-09-06-jar-exp-0013-runtime-acceleration-design.md`

## Global Constraints

- Experiment ID is exactly `JAR-EXP-0013`.
- Source pins remain: ISR `f9fd62d57408308788822162d9ded7d9741dbb10`, ToolRush `4ecd8810fdc9e6e0c64af3d532f876d06f6a278e`, Obscura `a1e09de68c7617b8079fbb1661b0548c501971c1`.
- No production changes to WORKS, Trust Gateway, AIE, or governance contracts.
- Primary performance evidence comes from a controlled real Windows Hermes host, not GitHub-hosted runner timings.
- Confirmatory mission efficacy needs at least 100 total verified mission attempts per condition.
- Mission-success non-inferiority margin is exactly 5 percentage points absolute.
- Raw completed-run evidence is append-only and secrets are never persisted.
- TDD applies to production Python behavior: failing test first, verify RED, minimal implementation, verify GREEN.
- No anti-bot, CAPTCHA-bypass, or access-control bypass claim is in scope.

---

### Task 1: Freeze protocol, source pins, and registry identity

**Files:**
- Create: `experiments/runtime_acceleration/__init__.py`
- Create: `experiments/runtime_acceleration/protocol.py`
- Create: `experiments/runtime_acceleration/protocol.yaml`
- Create: `experiments/runtime_acceleration/preregistration.md`
- Create: `experiments/runtime_acceleration/README.md`
- Create: `data/runtime_acceleration/manifests/source_pins.json`
- Modify: `data/experiment_registry.csv`
- Test: `tests/runtime_acceleration/test_protocol.py`

**Interfaces:**
- Produces `load_protocol(path) -> dict`, condition IDs `A/B/C/D`, frozen source pins, and exactly one registry row for `JAR-EXP-0013`.

- [ ] **Step 1: Write the failing protocol test**

```python
from pathlib import Path
from experiments.runtime_acceleration.protocol import load_protocol

ROOT = Path(__file__).resolve().parents[2]


def test_protocol_freezes_conditions_thresholds_and_source_pins():
    protocol = load_protocol(ROOT / "experiments/runtime_acceleration/protocol.yaml")
    assert list(protocol["conditions"]) == ["A", "B", "C", "D"]
    assert protocol["thresholds"]["tool_overhead_reduction_min"] == 0.30
    assert protocol["thresholds"]["combined_mission_wall_reduction_min"] == 0.15
    assert protocol["thresholds"]["mission_success_noninferiority_margin"] == 0.05
    assert protocol["confirmatory"]["minimum_mission_attempts_per_condition"] == 100
    assert protocol["pins"]["toolrush"] == "4ecd8810fdc9e6e0c64af3d532f876d06f6a278e"
    assert protocol["pins"]["obscura"] == "a1e09de68c7617b8079fbb1661b0548c501971c1"
```

- [ ] **Step 2: Run RED**

Run: `pytest tests/runtime_acceleration/test_protocol.py -q`
Expected: FAIL because `experiments.runtime_acceleration.protocol` does not exist.

- [ ] **Step 3: Implement the minimal protocol loader and frozen YAML**

```python
from pathlib import Path
import yaml


def load_protocol(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data.get("experiment_id") != "JAR-EXP-0013":
        raise ValueError("unexpected experiment_id")
    return data
```

The YAML encodes all four conditions, exact pins, repetition floors, primary metrics, the `0.05` margin, and G-TR/G-OB/G-COMB thresholds exactly as approved.

- [ ] **Step 4: Run GREEN and registry validation**

Run: `pytest tests/runtime_acceleration/test_protocol.py -q`
Expected: PASS.

Run: `python - <<'PY'\nimport csv\nrows=list(csv.DictReader(open('data/experiment_registry.csv', encoding='utf-8')))\nassert sum(r['experiment_id']=='JAR-EXP-0013' for r in rows)==1\nPY`
Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
git add experiments/runtime_acceleration data/runtime_acceleration/manifests/source_pins.json data/experiment_registry.csv tests/runtime_acceleration/test_protocol.py
git commit -m "research: freeze JAR-EXP-0013 protocol"
```

### Task 2: Environment capture and append-only evidence contract

**Files:**
- Create: `experiments/runtime_acceleration/environment.py`
- Create: `experiments/runtime_acceleration/evidence.py`
- Test: `tests/runtime_acceleration/test_environment.py`
- Test: `tests/runtime_acceleration/test_evidence.py`

**Interfaces:**
- `capture_environment() -> dict`.
- `write_run_evidence(root, run_id, payloads) -> Path` creates `metadata.json`, `metrics.json`, `stdout.log`, `stderr.log`, `verifier.json`, `artifacts.sha256` and rejects overwrite of a completed run.

- [ ] **Step 1: Write failing tests for required environment fields and append-only evidence**
- [ ] **Step 2: Run RED and confirm failure is missing implementation**
- [ ] **Step 3: Implement non-secret environment capture and atomic SHA-256 evidence writer**
- [ ] **Step 4: Run GREEN**
- [ ] **Step 5: Commit `research: add reproducible evidence contract`**

### Task 3: Differential result model and negative controls

**Files:**
- Create: `experiments/runtime_acceleration/verification/differential.py`
- Create: `experiments/runtime_acceleration/verification/negative_controls.py`
- Test: `tests/runtime_acceleration/test_differential.py`
- Test: `tests/runtime_acceleration/test_negative_controls.py`

**Interfaces:**
- `compare_observable(control, treatment) -> DifferentialResult` with fields `equal`, `classification`, `details`.
- `assert_negative_control_failed(result, expected_assertion) -> None`.

- [ ] **Step 1: RED tests for semantic mismatch, error-class mismatch, and a control that incorrectly passes**
- [ ] **Step 2: Verify RED**
- [ ] **Step 3: Implement stable normalized comparison without coercing mismatches to PASS**
- [ ] **Step 4: Verify GREEN**
- [ ] **Step 5: Commit `research: add differential verification contracts`**

### Task 4: Deterministic trace schema and replay

**Files:**
- Create: `experiments/runtime_acceleration/traces.py`
- Create: `experiments/runtime_acceleration/runners/trace_replay.py`
- Create: `experiments/runtime_acceleration/workloads/trace_replay.yaml`
- Test: `tests/runtime_acceleration/test_trace_replay.py`

**Interfaces:**
- `load_trace(path) -> list[TraceStep]`.
- `replay_trace(steps, adapter) -> list[dict]` where adapter exposes `execute(operation, payload)`.

- [ ] **Step 1: RED test proving order and observable outputs are preserved**
- [ ] **Step 2: Verify RED**
- [ ] **Step 3: Implement pure replay plus per-step monotonic timing in persisted runner output**
- [ ] **Step 4: Verify GREEN**
- [ ] **Step 5: Commit `research: add deterministic trace replay`**

### Task 5: Tool adapters and microbenchmarks

**Files:**
- Create: `experiments/runtime_acceleration/adapters/base.py`
- Create: `experiments/runtime_acceleration/adapters/stock_hermes.py`
- Create: `experiments/runtime_acceleration/adapters/toolrush.py`
- Create: `experiments/runtime_acceleration/runners/microbench.py`
- Create: `experiments/runtime_acceleration/workloads/tool_microbench.yaml`
- Test: `tests/runtime_acceleration/test_tool_adapters.py`
- Test: `tests/runtime_acceleration/test_microbench.py`

**Interfaces:**
- `ToolAdapter.execute(operation, payload) -> dict`.
- `run_microbenchmark(..., warm_repetitions=20) -> dict` returns cold sample where relevant, all raw warm samples, median, p95, min, max.

- [ ] **Step 1: RED tests for explicit treatment gating and raw-sample retention**
- [ ] **Step 2: Verify RED**
- [ ] **Step 3: Implement subprocess/config wrappers; do not vendor ToolRush**
- [ ] **Step 4: Verify GREEN**
- [ ] **Step 5: Commit `research: add ToolRush microbenchmark lane`**

### Task 6: Browser provider contract and deterministic fixture conformance

**Files:**
- Create: `experiments/runtime_acceleration/adapters/browser_base.py`
- Create: `experiments/runtime_acceleration/adapters/chromium.py`
- Create: `experiments/runtime_acceleration/adapters/obscura.py`
- Create: `experiments/runtime_acceleration/fixture_server.py`
- Create: `experiments/runtime_acceleration/verification/browser_conformance.py`
- Create: `experiments/runtime_acceleration/workloads/browser_compat.yaml`
- Test: `tests/runtime_acceleration/test_fixture_server.py`
- Test: `tests/runtime_acceleration/test_browser_conformance.py`

**Interfaces:** Browser adapters expose `start`, `navigate`, `evaluate`, `query`, `screenshot`, `close`. Conformance reports passed/total, observables, and explicit `UNAVAILABLE`/`UNSUPPORTED` classifications.

- [ ] **Step 1: RED tests for static DOM, JS mutation, redirect, form echo, cookie roundtrip, slow response, and deterministic 500 fixture routes**
- [ ] **Step 2: Verify RED**
- [ ] **Step 3: Implement stdlib local fixture server and provider wrappers**
- [ ] **Step 4: Verify GREEN offline with a deterministic fake provider; host smokes are integration-only**
- [ ] **Step 5: Commit `research: add browser conformance harness`**

### Task 7: Mission runner, counterbalanced factorial schedule, verifier authority

**Files:**
- Create: `experiments/runtime_acceleration/runners/mission_bench.py`
- Create: `experiments/runtime_acceleration/runners/factorial.py`
- Create: `experiments/runtime_acceleration/workloads/coding_missions.yaml`
- Create: `experiments/runtime_acceleration/workloads/mixed_agent_missions.yaml`
- Test: `tests/runtime_acceleration/test_mission_bench.py`
- Test: `tests/runtime_acceleration/test_factorial.py`

**Interfaces:**
- `build_counterbalanced_schedule(missions, conditions, seed) -> list[dict]`.
- `run_mission(mission, treatment, verifier) -> MissionResult`; only verifier PASS can set verified success.

- [ ] **Step 1: RED tests for deterministic seeded balancing and verifier authority**
- [ ] **Step 2: Verify RED**
- [ ] **Step 3: Implement result model and seeded schedule**
- [ ] **Step 4: Verify GREEN**
- [ ] **Step 5: Commit `research: add factorial mission benchmark`**

### Task 8: Statistical analysis and promotion gates

**Files:**
- Create: `experiments/runtime_acceleration/analysis/analyze.py`
- Create: `experiments/runtime_acceleration/analysis/report.py`
- Create: `tests/runtime_acceleration/fixtures/evidence/control.json`
- Create: `tests/runtime_acceleration/fixtures/evidence/treatment.json`
- Test: `tests/runtime_acceleration/test_analysis.py`
- Test: `tests/runtime_acceleration/test_promotion_gates.py`

**Interfaces:**
- `bootstrap_median_difference(control, treatment, seed, resamples=10000) -> dict`.
- `wilson_interval(successes, total, z=1.959963984540054) -> tuple[float, float]`.
- `evaluate_gates(results, protocol) -> dict` returning `PASS`, `FAIL`, or `INCONCLUSIVE` for each gate.

- [ ] **Step 1: RED tests proving 99 attempts is INCONCLUSIVE, 14% combined speedup fails 15%, and any new correctness failure forces FAIL**
- [ ] **Step 2: Verify RED**
- [ ] **Step 3: Implement seeded stdlib statistics and immutable-threshold gate evaluator**
- [ ] **Step 4: Verify GREEN**
- [ ] **Step 5: Commit `research: add statistical gate analysis`**

### Task 9: Host preflight and CI reproducibility

**Files:**
- Create: `experiments/runtime_acceleration/host_preflight.py`
- Create: `.github/workflows/jar-exp-0013.yml`
- Modify: `experiments/runtime_acceleration/README.md`
- Test: `tests/runtime_acceleration/test_host_preflight.py`

**Interfaces:** `check_preflight(snapshot, limits) -> dict` returns `clean` and explicit contamination reasons.

- [ ] **Step 1: RED tests for CPU/memory contamination rules**
- [ ] **Step 2: Verify RED**
- [ ] **Step 3: Implement preflight plus Windows/Ubuntu functional CI; hosted timing is never authoritative**
- [ ] **Step 4: Run the full JAR-EXP-0013 unit suite GREEN**
- [ ] **Step 5: Commit `ci: add JAR-EXP-0013 reproducibility gates`**

### Task 10: Dry-run readiness and experiment handoff

**Files:**
- Create: `experiments/runtime_acceleration/dry_run.py`
- Create: `JAR-EXP-0013-RUNTIME-ACCELERATION.md`
- Create: `data/runtime_acceleration/evidence/readiness.json`
- Test: `tests/runtime_acceleration/test_dry_run.py`

**Interfaces:** `run_dry_run(root) -> dict` validates protocol, pins, fixture server, replay, evidence, gate evaluator and negative-control definitions without provider spend or production mutation.

- [ ] **Step 1: RED test requiring `live_provider_calls == 0`, `production_mutations == 0`, and `READY_FOR_CONTROLLED_HOST_RUN`**
- [ ] **Step 2: Verify RED**
- [ ] **Step 3: Implement disposable offline dry-run orchestration with explicit host-integration blockers**
- [ ] **Step 4: Run full verification: `pytest tests/runtime_acceleration -q` and `python -m experiments.runtime_acceleration.dry_run`**
- [ ] **Step 5: Commit `research: complete JAR-EXP-0013 harness readiness`**

## Plan self-review

- Spec coverage: all approved deliverables map to Tasks 1–10. Controlled-host raw evidence and the confirmatory 100-attempt runs remain post-harness execution; no measurements are fabricated during implementation.
- Placeholder scan: no TBD/TODO or threshold placeholders.
- Type consistency: protocol, adapters, verifier, mission result, evidence writer, analysis, and gate evaluator interfaces are stable across tasks.
- Scope check: this remains one research harness and does not cross the production boundary.
