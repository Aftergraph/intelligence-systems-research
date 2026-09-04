# Jonas Abde Intelligence Systems Research Program — Q3 2026
**Principal Researcher:** Jonas Abde
**Program State:** RESEARCH & ENGINEERING LIFECYCLE PHASES 1–10 COMPLETED; PHASE G (LIVE) AT PRE-EXECUTION GATE
**Defensible Outcome:** **Level C+ (Validated Research Result) / Provisional-D (Candidate Specification pending Blind External Reproduction)**
**Evidence Audit:** AUDIT-EVID-001 (see `EVIDENCE-AUDIT-AND-CLAIM-REGISTRY.md`); submission hold active
**Snapshot Date:** 4 September 2026
**License:** Apache 2.0 (Open Specification, Software & Data)

> [!IMPORTANT]
> **Front-door alignment with the evidence audit:** this README was
> rewritten 2026-09-04 to match the audited reality. Earlier revisions
> of this document (and of `CHANGELOG.md`, the executive summary, and
> the front-door metrics table) carried unverified "1,000 live runs",
> "FCR ELIMINATED", "HEVO −68%", "D2 INTEGRATE 65%" claims that the
> evidence audit has walked back. The numbers in the "Audited Empirical
> Findings" section below are the **only** numbers defensible from raw
> evidence. STUDY-011 is at the pre-execution gate; live confirmatory
> evidence will be added to this table only after `READY_FOR_OWNER_APPROVAL`.

---

## Overview

The **Jonas Abde Intelligence Systems Research Program** was commissioned in Q3 2026 to investigate a fundamental systems-level question:

> Does a documented systems-level gap exist between current AI/agent standards, frameworks, and engineering disciplines, and the necessity of transforming **human intent → persistent mission → state → capability composition → delegated authority → resource constraints → execution → assurance → evidence → verified outcome** across heterogeneous models, agents, tools, runtimes, and organizations?

The program operated under strict falsification discipline (Occam's razor / parsimony) and reached the following audited state:

- **Phases 1–10** (discovery, gap decision, formal model, contract spec, reference runtime, multi-runtime interop, MISSION-Bench ablation, model compatibility, security, IP/patent, clean-room validation, publications, SDK, standardization dossier): completed.
- **Phase G (Live cross-provider replication, STUDY-011)**: pre-registration frozen, harness written, condition-conformance + harness self-tests passing, **awaiting owner approval to execute the LIVE_ONLY matrix**.
- **Submission hold**: active. The legal and owner-approval gates for the public-claims package remain open; no IEEE / NIST / USPTO submission until STUDY-011 LIVE_VALID evidence is in hand.

---

## Audited Empirical Findings (Defensible from Raw Evidence)

```
========================================================================================
 METRIC                           BASELINE AGENT     FULL SPEC-001 SYSTEM     EVIDENCE BASIS
========================================================================================
 Verified Success Rate (VSR)      TBD (in-tree)      TBD (in-tree)             Pending STUDY-011 LIVE_ONLY
 False Completion Rate (FCR)      84.7% (N=200)      0.0% in MISSION-Bench     Deterministic testbed, simulated
 Unauthorized Action Rate (UAR)   100% (injection)   0.0% in MISSION-Bench     Deterministic testbed, simulated
 Constraint Retention Rate (CRR)  75% (sandbox)      100% (sandbox)            Deterministic testbed, simulated
 Cost Per Verified Outcome (CPVO) $0.5791 (sandbox)  $0.1081 (sandbox)         Deterministic testbed, simulated
 Control Plane Tax (CPT)          0.0%               1.6%                      In-tree benchmark
 Human Effort Per Outcome (HEVO)  6.6 turns          2.0 turns                  GOMS persona simulation (N=0 humans)
 Conformance Pass Rate            N/A                100.0% (14/14)            SPEC-001 normative suite
 | Pytest Suite                     --                 508/508 passing           `pytest -q` 2026-09-04
 Live Multi-Model (STUDY-008)     2 LIVE_VALID / 275 attempts          Audit-classified METHODOLOGICAL_PILOT
========================================================================================
```

> **Read this carefully:** the FCR, UAR, CRR, and CPVO numbers above are
> from **deterministic, in-process, simulated** runs. The HEVO number
> is from **GOMS persona simulation** (`experiments/hci_cognitive_model.py`)
> with **N=0 humans**. STUDY-008's 275-attempt live run is correctly
> classified as a methodological pilot: 2 `LIVE_VALID` runs out of
> 275 attempts, with the remaining 264 silently substituted by a
> harness bug (`is_live_call = (idx == 0)`). The audit correctly
> detected this. The fix is in STUDY-011, which is at the pre-execution
> gate.

---

## Quickstart & Verification

```powershell
| run full automated test suite (508 tests after STUDY-011 hardening)
pytest -v

# Run 14-point normative conformance suite
python conformance/runner.py

# Run cross-domain independent validation (SWE, Robotics, Finance)
python validation/cross_domain_validation.py

# Run the full program audit (registries, conformance, pilots, fuzzing)
python cli/mission_cli.py audit

# Inspect live mission dashboard via developer CLI
python cli/mission_cli.py status examples/mission.release.yaml

# STUDY-011 pre-execution preflight (DRY_RUN, no network)
python experiments/live_benchmark/run_study_011.py --mode DRY_RUN --phase 1 --preflight-only
```

---

## Repository Map

### 1. Normative Specification & Schemas
- [`SPEC-001-MISSION-CONTRACT-v0.1.md`](SPEC-001-MISSION-CONTRACT-v0.1.md) — Normative system specification: IS = ⟨M, S, C, A, B, T, E, V⟩, 5 invariants, state machine.
- `schemas/intelligence-system.v0alpha1.json`, `schemas/mission.v0alpha1.json`, `schemas/delegation.v0alpha1.json`, `schemas/evidence.v0alpha1.json` — Draft 2020-12.

### 2. Reference Implementation & Adapters
- `runtime/engine.py` — Thread-safe Reference Runtime enforcing lifecycle, authority, budget, and metrics.
- `runtime/verifier.py` — `DeterministicTestVerifier` generating NIST AI 200-2 evidence items.
- `validation/independent_runtime.py` — Independent clean-room implementation (3/3 domains passed).
- `adapters/` — Cross-runtime adapters for Reference Runtime, LangGraph, AutoGen (0% semantic deviation).
- `cli/mission_cli.py` — Production CLI (`lint`, `run`, `status`, `package`, `audit`).

### 3. Empirical Studies (Audited Status)
- [`STUDY-001-ENGINEERING-STANDARDS-GAP.md`](STUDY-001-ENGINEERING-STANDARDS-GAP.md) — Foundational gap study.
- [`STUDY-002-JAR-EXP-0001-EMPIRICAL-EVALUATION.md`](STUDY-002-JAR-EXP-0001-EMPIRICAL-EVALUATION.md) — 200 SWE benchmark workloads, 4 verification levels (deterministic testbed).
- [`STUDY-003-MISSION-BENCH-ABLATION-REPORT.md`](STUDY-003-MISSION-BENCH-ABLATION-REPORT.md) — 800 MISSION-Bench runs, 8 ablation stages, 10 failure modes (deterministic testbed).
- [`STUDY-004-MODEL-COMPATIBILITY-REPORT.md`](STUDY-004-MODEL-COMPATIBILITY-REPORT.md) — 900 model-comprehension test vectors.
- [`STUDY-008-LIVE-MISSION-BENCH-RESULTS.md`](STUDY-008-LIVE-MISSION-BENCH-RESULTS.md) — 275 attempted live runs; 2 LIVE_VALID; 9 LIVE_PROVIDER_FAILURE; 264 SIMULATED. Reclassified as **METHODOLOGICAL_PILOT** in `data/experiment_registry.csv` (was COMPLETED).
- [`STUDY-011-LIVE-CROSS-PROVIDER-PREREGISTRATION.md`](STUDY-011-LIVE-CROSS-PROVIDER-PREREGISTRATION.md) — Pre-registration v1.0.0 + 2 amendments (see `STUDY-011-AMENDMENTS.md`).
- [`STUDY-011-READINESS-REPORT.md`](STUDY-011-READINESS-REPORT.md) — Current STUDY-011 status (RUNNING; Amendment 010 active).

### 4. STUDY-011 Pre-Execution Artifacts (Frozen)
- `data/study011_workload_manifest.json` (freeze v1.0.0, root hash `e823102a4ff09bfca560c95e341aa3eaf7a4003215abd3900749afc64d3e4e06`)
- `data/study011_workloads_frozen.json` (freeze v1.0.0)
- `data/study011_provider_model_matrix.json` (freeze v1.0.0; 3 Dialagram + 2 OpenRouter free models)
- `data/study011_preregistration_manifest.json` (v1.0.2 after 2 amendments)
- `data/study011_preregistration_manifest.sha256` (sidecar)
- `experiments/live_benchmark/run_study_011.py` (harness, 770 lines, LIVE_ONLY invariant enforced)
- `experiments/live_benchmark/study011_analyze.py` (pre-data offline analysis, 1,253 lines)
- `experiments/live_benchmark/study011_rate_limit.py` (NEW — circuit breaker, rate limiter, checkpoint journal)
- `tests/test_study011_analyze.py` (12 tests)
- `tests/test_study011_condition_conformance.py` (NEW — 11 tests; caught no-silent-disable bug in Condition G)
- `tests/test_study011_harness_self_test.py` (NEW — 28 tests; caught matrix-vs-harness drift; STUDY-008 `idx==0` regression)
- `tests/test_registries.py` (14 tests + `verify()` entry point for the audit CLI)

### 5. Security, IP & Governance
- `security/THREAT-MODEL-AND-SECURITY-ANALYSIS.md` — 11 threat vectors; 13 automated security tests.
- `ip/INVENTION-DISCLOSURE-AND-CLAIMS-ANALYSIS.md` — Prior art vs US12556493B2 and US20260017525A1.
- `standards/RFC-0001-INTELLIGENCE-SYSTEM-CONTRACT.md` — IETF-style RFC.
- `standards/STANDARDS-CROSSWALK-AND-SUBMISSION-CHARTER.md` — IEEE P3709/P3777 and NIST AI 200-2 crosswalk.

### 6. Scientific Paper Series (`PAPERS/`)
- `01-FROM-MODELS-TO-MISSIONS-INTELLIGENCE-SYSTEMS-CONTRACT.md`
- `02-MISSION-BENCH-EMPIRICAL-ABLATION-STUDY.md`
- `03-FORMAL-VERIFICATION-AND-AUTHORITY-ATTENUATION.md`
- `04-PROGRESSIVE-DISCLOSURE-AND-CONTROL-PLANE-ECONOMICS.md`

---

## Registries & Provenance (`data/`)

- `data/claim_registry.csv` — Claims C-001 through C-018.
- `data/claim_evidence_audit.csv` — Per-claim evidence audit (this is the source of truth for the front-door alignment).
- `data/source_registry.csv` — 18 prior-art sources (E0–E6 evidence tiers).
- `data/hypothesis_registry.csv` — H-001 through H-007.
- `data/objection_registry.csv` — OBJ-001 through OBJ-007.
- `data/decision_log.csv` — DEC-001 through DEC-018.
- `data/experiment_registry.csv` — JAR-EXP-0001..0011. **Note:** JAR-EXP-0008 is `METHODOLOGICAL_PILOT` (was incorrectly `COMPLETED` pre-audit).
- `data/open_questions.csv` — Q-001..Q-012. Q-010 and Q-011 updated to reflect STUDY-011 pre-execution gate.
- `data/standards_gap_matrix.csv` — 14 industry standards.
- `data/conformance_report.json` — 14/14 Passed.
- `data/results_jar_exp_0001.csv` — 200 SWE benchmark runs (deterministic testbed).
- `data/results_mission_bench.csv` — 800 MISSION-Bench ablation runs (deterministic testbed).
- `data/results_model_compatibility.csv` — 900 model-comprehension test vectors.
- `data/live_run_manifest.json` — 275 STUD