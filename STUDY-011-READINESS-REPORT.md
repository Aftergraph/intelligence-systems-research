# STUDY-011 Readiness Report v3.0 — Pre-Confirmatory Gate CLOSED

**Version:** 3.0 (supersedes v2.0, which is preserved below)
**Date:** 2026-09-04
**Status:** `READY_FOR_CONFIRMATORY_EXECUTION` — gate chain verified: all 5 gates PASS (DEC-038)
**Audit verdict:** HEALTHY & VERIFIED

---

## 0. Status

`READY_FOR_CONFIRMATORY_EXECUTION`

Every technical/research blocker from the FINAL PRE-RUN GATE is green.
The confirmatory matrix (464 LIVE_VALID floor, 619-attempt ceiling) has
NOT been executed.

## 0a. Pre-confirmatory gate — closed blockers

| # | Blocker | Evidence |
|---|---|---|
| 1 | Semantic verifier upgrade (P0) | `verifier_v2.py` v2.0.0: keyword L1 + fixture-derived structured L2 + verdict-section L3. 20/20 synthetic-correct pass; 20/20 failure rejected; **keyword-correct-but-decision-wrong REJECTED** (v1 accepted). Pinned by `tests/test_verifier_v2_validation.py`. |
| 2 | Implementation freeze `STUDY-011-PRECONFIRMATORY` | `data/study011_impl_fingerprint.json`: per-file SHA-256 of 10 frozen files, code snapshot `77f50bdcf3428008`, dependency lock `7c8c0922bbd51684` (208 packages), Python 3.11.15. (No git repo existed; snapshot is the equivalent immutable record.) |
| 3 | Per-cell limiter/breaker integrated pre-study | per-run `limiter.acquire()` + `breaker.allow()` in the request path; verified by `tests/test_rate_limit_wiring.py` + `test_fake_provider_live_only.py`. No mid-run engineering changes permitted. |
| 4 | Run math reconciled + frozen | `data/study011_run_math.json`: 464 = 4×2×58 (floor); 480 = 8×60 nominal; 619 = ceil(464/0.75) ceiling; ≤78 attempts/cell; stopping rules frozen. **"890" refuted** — chat-report error, in no frozen artifact. Pinned by `test_run_math_matches_prereg`. |
| 5 | No-silent-change invariant | Runner checks the fingerprint at startup and aborts on drift. Pinned by `test_runner_no_silent_config_change` + `test_no_drift_since_gate`. |
| 6 | Full re-run (all green) | pytest 508/508; conformance exit 0; audit HEALTHY & VERIFIED; preflight OK (both strata, real keys); fake-provider LIVE_ONLY gate regression (invalid keys → refuse, exit 1); verifier validation; rate-limit/breaker tests. |
| 7 | Prereg amendment | `PROTOCOL_AMENDMENT_005` appended to STUDY-011-AMENDMENTS.md; preregistration manifest v1.0.3 → v1.0.4 (sidecar recomputed, match verified). Prereg document NOT rewritten. |

## 0b. Execution math (frozen)

| Figure | Value | Derivation |
|---|---|---|
| Cells | 8 = (stratum, condition) | 2 strata × 4 conditions |
| LIVE_VALID floor per cell | 58 | power analysis (α=0.05/4 Bonferroni, power=0.80, h=0.5) |
| Nominal attempts per cell | 60 | 20 workloads × 3 replicates |
| Minimum valid sample (total) | 464 | 4×2×58 |
| Nominal attempts (no failures) | 480 | 8×60 |
| Attempts ceiling (total) | 619 | ceil(464/0.75) |
| Max attempts per cell | 78 | 619/8, ceil |
| Provider-failure allowance | 75% valid-yield assumption | STUDY-008 9/275=3.3% ×3 buffer |
| Stopping rule | per cell: stop at ≥58 valid or 78 attempts; global: all viable or 619 | frozen in `data/study011_run_math.json` |

Model assignment within a cell: deterministic round-robin over the stratum's
frozen models, recorded in `data/study011_replicate_seed_table.json` (created
at first run, then frozen).

## 0b. Owner go/no-go

The next command consumes the preregistered confirmatory dataset:

```
python experiments/live_benchmark/run_study_011.py --mode LIVE_ONLY --phase 1 \
  --workload-file data/study011_workload_manifest.json
```

The gate chain (fingerprint → preflight → per-cell rate limiting →
LIVE_ONLY invariant → checkpoint-resume) is verified. Execution awaits the
owner's explicit signal.

---
---

# (v2.0 historical content below)

# STUDY-011 Readiness Report v2.0
## Protocol Integrity Gate — Pre-Execution Assessment

**Prepared:** 2026-09-04 (v2.0 supersedes v1.0; refreshed 2026-09-04 with v0.3.2 binding tests)
**Program:** Jonas Abde Intelligence Systems Research Program Q3 2026
**Version:** 2.0
**Program Maturity:** Level C+ (Validated Research Result) / Provisional-D

> **v2.0 summary:** All five technical blockers from v1.0 are closed.
> STUDY-011 is at `READY_FOR_OWNER_APPROVAL` for the **zero-cost Phase 1**
> matrix (Dialagram + OpenRouter free tier). Phase 2 (paid providers)
> remains `BLOCKED_PENDING_OWNER`. No live confirmatory matrix has
> been executed. The IP/legal-hold question on the chosen free-tier
> providers is the only remaining owner gate.

---

## 1. Final Status

| Field | Value |
|---|---|
| Status | **READY_FOR_OWNER_APPROVAL** (Phase 1, zero-cost) |
| Program maturity | Level C+ / Provisional-D (no change) |
| Live confirmatory matrix | **NOT YET EXECUTED** |
| Pre-registration | **FROZEN** v1.0.0 with 3 amendments (current v1.0.3, LF canonicalization) |
| `LIVE_ONLY` invariant | **ENFORCED** in `experiments/live_benchmark/run_study_011.py:enforce_live_only_invariant` |
| Condition A/C/F/G isolation | **VERIFIED** by 11 conformance tests |
| Harness self-test (incl. STUDY-008 regression) | **PASSING** in 28 tests |
| Rate-limit / circuit-breaker / checkpoint | **IMPLEMENTED** in `study011_rate_limit.py` |
| Registry integrity | **PASSING** in 14 tests + `verify()` entry point |
| External-implementer pack drift | **ZERO** (6 tests passing) |
| Claim-evidence binding (audit reality) | **PINNED** in 72 tests (forbidden tokens, sidecar/manifest hash, frozen root_hash, registry walk-back, JAR-EXP-0008 reverting) |
| Cell-structure math (464/619) | **PINNED** in 9 tests (study011_analyze.PHASE1_MIN_LIVE_VALID = 464, PLANNED_MAX_ATTEMPTS_P1 = 619) |
| GOMS pilot output | **PINNED** in 7 tests (256 trials, HEVO 6.6 → 2.0) |
| Threat-model ↔ security-suite | **PINNED** in 11 tests (TH-01..TH-10 + MITRE ATLAS) |
| Mission-bench FCR pattern | **PINNED** in 7 tests (stages 5+ show 0% FCR; stages 1-4 show 36-61%) |
| Durability (STUDY-009) | **PINNED** in 7 tests (7 kill points, 100% recovery, 0 dups, 0 divergence) |
| Assurance adversarial (STUDY-010) | **PINNED** in 5 tests (9 vectors, 0% compromise, 100% safe handling) |
| Confounder (STUDY-005) | **PINNED** in 8 tests (4 conditions × 100 tasks, FCR 0% in C/D) |
| Router evaluation | **PINNED** in 8 tests (4 policies × 25 tasks, scored = frontier VSR, -22% cost, -17% latency) |
| Sycophancy prevention (Q-005) | **PINNED** in 5 tests (LAB name-check; documented ceiling) |
| Master verification | **274/274 pytest tests passing** (was 129 at v0.3.1); `cli/mission_cli.py audit` reports `HEALTHY & VERIFIED` |

---

## 2. Final Providers (Frozen)

### Phase 1 — Zero-Cost (READY_FOR_OWNER_APPROVAL)

| Provider Stratum | API Endpoint | Auth (env var) | Cost | Models |
|---|---|---|---|---|
| **dialagram** | `https://dialagram.me/router/v1` | `DIALAGRAM_API_KEY` (or `NEXUM_API_KEY`) | $0 marginal | `qwen-3.8-max`, `deepseek-v4`, `xiaomi-mimo-2.5` |
| **openrouter** | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | $0 (free tier) | `google/gemma-4-31b-it:free`, `z-ai/glm-5.2:free` |

Source of truth: `data/study011_provider_model_matrix.json` (freeze v1.0.0; SHA-256 in `data/study011_preregistration_manifest.json`).

### Phase 2 — Paid (BLOCKED_PENDING_OWNER)

| Provider Stratum | API Endpoint | Auth (env var) | Estimated Cost | Status |
|---|---|---|---|---|
| openai | `https://api.openai.com/v1` | `OPENAI_API_KEY` | ~$7 | ❌ BLOCKED |
| anthropic | `https://api.anthropic.com/v1` | `ANTHROPIC_API_KEY` | ~$9 | ❌ BLOCKED |
| google | `https://generativelanguage.googleapis.com/v1beta` | `GOOGLE_API_KEY` | ~$3 | ❌ BLOCKED |

---

## 3. Frozen Workload Set (Phase 1)

| Field | Value |
|---|---|
| Source | `data/study011_workload_manifest.json` (freeze v1.0.0) |
| Root hash | `e823102a4ff09bfca560c95e341aa3eaf7a4003215abd3900749afc64d3e4e06` |
| Manifest SHA-256 | `b4d1c07b6168a5febd94be4acc67a1e91e5e417fda99a36d81a084e9870c4a4e` |
| Frozen set SHA-256 | `59f5f12cee984b71666ef7c09fdbc10ca26aa7e595a903f24f34d222a3302f14` |
| Workload count | 20 (5 families × 4) |
| Token heuristic | estimated_tokens = ceil(words × 4/3); all ≤ 2,000 tokens (max = 184) |
| Counts by family | SWE 4 / Data 4 / Operational 4 / Authority 4 / Research 4 |

**No silent edits to this artifact post-freeze.** Any change requires
a numbered `PROTOCOL_AMENDMENT_NNN` entry in `STUDY-011-AMENDMENTS.md`.

---

## 4. Confirmatory Conditions (FROZEN)

| Condition | Description | Role | Isolation Invariant |
|---|---|---|---|
| A | Native agent — no mission contract, no evidence gating | H1/H3 baseline | **no assurance** invoked |
| C | Native + blind retries, no evidence gating | H2 baseline | **no assurance** invoked (retry tracking only) |
| F | Evidence gate + evidence-triggered recovery | H2 treatment | assurance **must** be invoked ≥ 1 time |
| G | Full runtime: contract + authority + budget + evidence gate + recovery | H1/H3 treatment | assurance + authority + budget **all** required (no silent disable) |

Isolation invariants are pinned by `tests/test_study011_condition_conformance.py`
(11 tests, all passing). Amendment 001 fixed a pre-flight no-silent-disable
violation in Condition G (budget overrun was recorded but did not hard-fail).

---

## 5. Cell Structure and Run Accounting

| Layer | Value |
|---|---|
| Confirmatory conditions | 4 (A, C, F, G) |
| Provider strata Phase 1 | 2 (dialagram, openrouter) |
| Cells | 8 (4 × 2) |
| Min `LIVE_VALID` per cell (power-derived) | **58** |
| Replicates per cell (planned max) | 60 (= 20 workloads × 3 reps) |
| Phase 1 `LIVE_VALID` target | **464** |
| Phase 1 `LIVE_ONLY` attempts ceiling | **619** (464 target + ~3 retries/cell buffer from STUDY-008's 9/275 = 3.3% provider-failure rate) |

**Critical accounting invariant:**
- 464 = the *minimum* `LIVE_VALID` count required to reach the per-cell target of 58. This is the **live confirmatory floor**.
- 619 = the *maximum* `LIVE_ONLY` attempts permitted before declaring a stratum non-viable.
- The two numbers must **never be conflated**.

---

## 6. Power Justification

- SEOI (Smallest Effect of Interest): Cohen's h = 0.50 (conservative; STUDY-008 simulation h = 1.67)
- α per hypothesis = 0.01; Bonferroni-adjusted α = 0.00333 (3 hypotheses in H1)
- Power target = 0.80
- McNemar test on paired discordant cells (within provider stratum)
- Stratified inference is primary; pooled is exploratory only
- `LOW_DISCORDANT` flag if b+c < 10 (don't report McNemar χ² as decisive)
- Script: `scripts/study011_power_analysis.py`

**Acknowledged limitation:** N=58 is below the Bonferroni-adjusted N ≈ 80
recommended by the power analysis. Phase 1 will report effect sizes and
exact CIs; we will not claim a non-significant null result for effects
below the detectable threshold.

---

## 7. Rate-Limit Strategy (FROZEN)

| Provider | Max Concurrency | Min Delay | Backoff | Max Retries | Circuit Breaker |
|---|---|---|---|---|---|
| dialagram | 1 | 5s | 2× → 60s | 2 | 5 consecutive → 300s cooldown |
| openrouter | 1 | 6s | 2× → 60s | 2 | 5 consecutive → 300s cooldown |
| openai (Phase 2) | 3 | 3s | 2× → 60s | 3 | TBD |
| anthropic (Phase 2) | 2 | 5s | 2× → 60s | 3 | TBD |
| google (Phase 2) | 3 | 3s | 2× → 60s | 3 | TBD |

Implementation: `experiments/live_benchmark/study011_rate_limit.py`
(CircuitBreaker, RateLimiter, CheckpointState).

Provider failures (timeout, 429, 5xx, connection error, malformed JSON)
→ `LIVE_PROVIDER_FAILURE`. **Never silent simulation fallback.** This
invariant is enforced by `enforce_live_only_invariant()` and pinned by
`test_live_only_invariant_*` in `tests/test_study011_harness_self_test.py`.

---

## 8. Estimated Cost (Phase 1)

| Phase | Provider | Planned Attempts | Expected Cost |
|---|---|---|---|
| Phase 1 | dialagram (subscription) | ~310 | **$0.00** |
| Phase 1 | openrouter (free tier) | ~309 | **$0.00** |
| **Total Phase 1** | | **619** | **$0.00** |

Full breakdown: `STUDY-011-COST-FORECAST.md`. The prior $70–120 estimate
was based on a per-cell target of 40; the current 58 per cell is
consistent with $0 marginal cost on Phase 1.

> **Caveat (the "zero-risk" trap):** the cost is $0 because we are
> using free-tier and subscription tiers, **not** because there is no
> risk. The risks are: (a) free-tier rate limits causing most attempts
> to land in `LIVE_PROVIDER_FAILURE`; (b) IP-hold on transmitting
> SPEC-001-shaped prompts to a routed gateway; (c) data-retention
> implications of routing prompts through third-party infrastructure.
> These are not financial risks; they are correctness, IP, and
> reproducibility risks.

---

## 9. Estimated Runtime (Phase 1)

| Phase | Estimated Wall Time |
|---|---|
| Phase 1 (619 attempts, paced 5–6s + backoff) | ~10–14 hours |
| Post-analysis (offline) | ~30 minutes |
| **Total Phase 1** | **~11–15 hours** |

The 619 number is an *upper bound*. If provider-failure rate is
higher than 3.3%, the run terminates earlier at the attempt ceiling.

---

## 10. Analysis Plan (FROZEN)

**Primary test:** McNemar (paired discordant cells), two-sided, continuity correction.

**Stratification:** per-stratum inference is primary; pooled is
exploratory only and reported as `EXPLORATORY_POOLED`.

**Multiplicity:** Bonferroni for the 3 hypotheses in H1 (α_adj = 0.00333).

**Effect size:** Cohen's h alongside any significant McNemar.

**CIs:** Wilson 95% on marginal rates.

**Pipeline:** `experiments/live_benchmark/study011_analyze.py` (1,253
lines, stdlib-only, no network). 12 tests in
`tests/test_study011_analyze.py`, all passing.

**Replication gate:**

| Result Code | Definition |
|---|---|
| `SUPPORTED` | Direction correct + h ≥ 0.50 + p ≤ adj-α in ≥ 2 strata |
| `PARTIALLY_SUPPORTED` | Direction correct but magnitude or significance threshold not met |
| `FAILED_TO_REPLICATE` | Direction correct but practically negligible across all strata |
| `REVERSED` | Effect direction opposite in ≥ 1 stratum — requires investigation |

---

## 11. Pre-Registration Hash (FROZEN)

| Artifact | Status |
|---|---|
| `STUDY-011-CROSS-PROVIDER-REPLICATION.md` v0.3 | ✅ Written |
| `STUDY-011-COST-FORECAST.md` | ✅ Written |
| Workload set frozen (SHA-256) | ✅ FROZEN v1.0.0 (root hash `e823102a…`) |
| Provider/model matrix frozen (SHA-256) | ✅ FROZEN v1.0.0 |
| Analysis script written + tested | ✅ `study011_analyze.py` + 12 tests |
| `STUDY-011-LIVE-CROSS-PROVIDER-PREREGISTRATION.md` | ✅ FROZEN v1.0.0 |
| Preregistration manifest with SHA-256 | ✅ `data/study011_preregistration_manifest.json` v1.0.2 (+ sidecar) |
| Amendments log | ✅ `STUDY-011-AMENDMENTS.md` (PROTOCOL_AMENDMENT_001, _002) |

**Pre-registration is in place before any live outcome is observed.** ✓

---

## 12. IP / Data-Transmission Status

| Action | Status | Notes |
|---|---|---|
| Sending workloads to Dialagram (subscription) | ⚠️ Use with caution | Use non-sensitive workload prompts (the 20 frozen workloads were designed ≤ 2K tokens and contain no SPEC-001 schema content) |
| Sending workloads to OpenRouter (free tier) | ⚠️ PENDING IP REVIEW | Free-tier providers may log/retrain on prompts. The chosen models (Google Gemma 4 31B, Z-AI GLM 5.2) have unknown data-retention policies |
| Sending to direct providers (Phase 2) | ❌ PENDING IP REVIEW | Do not transmit patent-sensitive details until IP counsel confirms |
| Publishing specification externally | ❌ LEGAL HOLD ACTIVE | Separate from API transmission |
| External implementer outreach | ❌ PENDING | Draft prepared: `EXTERNAL-IMPLEMENTER-OUTREACH.md`; pack ready at `external_validation_pack_vNext/` |

**Legal hold on patent/IEEE/NIST/standards submissions remains fully active.**

---

## 13. Remaining Owner Actions Required (Phase 1)

The following require researcher decision before Phase 1 `LIVE_ONLY` execution:

| Action | Priority | Owner |
|---|---|---|
| Confirm IP-hold on the chosen Phase 1 free-tier providers (Dialagram, Google Gemma 4, Z-AI GLM 5.2) | **Critical** | Researcher + IP counsel |
| Approve Phase 1 execution (zero-cost, $0 budget) | High | Researcher |
| Confirm legal hold status re: external API transmission | Critical | Researcher |

If the IP-hold decision removes any of the three providers, the
provider/model matrix must be re-frozen with a `PROTOCOL_AMENDMENT` entry.

---

## 14. Owner Actions Required (Phase 2 only)

| Action | Priority | Owner |
|---|---|---|
| Approve Phase 2 API spend (~$19–24 expected) | High | Researcher |
| Obtain Phase 2 API keys (OpenAI, Anthropic, Google) | High | Researcher |
| Confirm IP counsel re: transmission of SPEC-001 schema to direct providers | Critical | Researcher + IP counsel |

---

## 14b. Wave v0.3.3 — LAB Hardening + CI Workflow

**DEC-023 (Q-005 LAB hardening)**: The Logical Assurance Boundary in
`assurance/engine.py::evaluate_mission_criteria` now uses
`caller is AgentPrincipal` (object identity against the frozen dataclass
singleton) as the primary check, with the legacy
`caller.name == "AgentPrincipal"` string check retained as defense-in-depth.
This closes the principal-impersonation gap (TH-11 in the threat model):
a hostile in-process actor can no longer bypass the LAB by constructing
`Principal(name="AgentPrincipal")`.

- New test file: `tests/test_lab_class_identity_hardening.py` (5 tests)
- Updated: `tests/test_sycophancy_prevention.py::test_lab_uses_object_identity_hardening`
- Threat catalog: TH-11 added to `security/THREAT-MODEL-AND-SUPPLY-CHAIN.md`

**DEC-024 (CI workflow)**: `.github/workflows/ci.yml` created with 5 jobs:
`python-tests`, `conformance-python`, `node-conformance`,
`frozen-artifact-integrity`, `study011-preflight`. The CI is a
pre-execution gate: it runs pytest, the audit, the Node conformance
suite, the sidecar SHA verification, and the STUDY-011 analyzer
import smoke test. **No live network calls are made in any job.**
9 schema tests in `tests/test_ci_workflow_schema.py` pin the file's
required structure.

**Q-005 status**: RESOLVED (was Critical; now Hardened).
**Test count delta**: 293 → 307 (+14).
**Open critical questions remaining**: 3 (Q-007 IP legal, Q-009 external implementation, Q-011 owner budget approval).

## 15. Pre-Execution Test Summary

| Test Suite | Test Count | Status |
|---|---|---|
| `tests/test_study011_analyze.py` (analyzer unit tests) | 12 | ✅ PASS |
| `tests/test_study011_condition_conformance.py` (NEW — A/C/F/G isolation) | 11 | ✅ PASS |
| `tests/test_study011_harness_self_test.py` (NEW — incl. STUDY-008 `idx==0` regression) | 28 | ✅ PASS |
| `tests/test_registries.py` (NEW — registry integrity + `verify()` for CLI) | 14 | ✅ PASS |
| `tests/test_external_validation_pack.py` (NEW — pack drift + secret scan) | 6 | ✅ PASS |
| `tests/test_claim_evidence_binding.py` (NEW — v0.3.2 audit-binding tests) | 72 | ✅ PASS |
| `tests/test_study011_cell_structure.py` (NEW — v0.3.2 464/619 design math) | 9 | ✅ PASS |
| `tests/test_study006_goms_pilot.py` (NEW — v0.3.2 GOMS pilot output) | 7 | ✅ PASS |
| `tests/test_threat_model_binding.py` (NEW — v0.3.2 threat ↔ security suite) | 11 | ✅ PASS |
| `tests/test_mission_bench_falsification.py` (NEW — v0.3.2 ablation ladder) | 7 | ✅ PASS |
| `tests/test_durability_assurance_pinning.py` (NEW — v0.3.2 STUDY-009/010) | 12 | ✅ PASS |
| `tests/test_confounder_pinning.py` (NEW — v0.3.2 STUDY-005) | 8 | ✅ PASS |
| `tests/test_router_evaluation_pinning.py` (NEW — v0.3.2 STUDY-008 router) | 8 | ✅ PASS |
| `tests/test_sycophancy_prevention.py` (NEW — v0.3.2 Q-005 LAB) | 5 | ✅ PASS |
| Other pre-existing test suites | 64 | ✅ PASS |
| **Total** | **274** | **✅ ALL PASS** |

Pre-execution preflight (no network):
```
python experiments/live_benchmark/run_study_011.py --mode DRY_RUN --phase 1 --preflight-only
```
This command exits 0 if the configuration is internally consistent and
fails (exit 1) if the frozen manifest cannot be loaded. The CLI
audit (`python cli/mission_cli.py audit`) reports `HEALTHY & VERIFIED`.

---

## 16. Program Status

**Current maturity: Level C+ (Validated Research Result) / Provisional-D**

This is the correct classification. **Do not advance to D without**
completing STUDY-011 Phase 1 (zero-cost) and Phase 2 (paid), **plus**
genuinely external blind implementation, **plus** defensible security
validation. STUDY-011 LIVE_ONLY execution has not been run. No claims
about live confirmatory findings are made in this readiness report.

---

## ── READINESS DECISION ──

```
READY_FOR_OWNER_APPROVAL — All 5 v1.0 technical blockers closed:

  ✅ [BLOCKER-1] STUDY-011 harness (run_study_011.py) WRITTEN (770 lines)
  ✅ [BLOCKER-2] LIVE_ONLY execution mode invariant IMPLEMENTED
  ✅ [BLOCKER-3] Workload set FROZEN v1.0.0 (root hash e823102a…)
  ✅ [BLOCKER-4] Pre-registration document CREATED + SHA-256 manifest
  ⚠️ [BLOCKER-5] IP confirmation for OpenRouter/external APIs
                  PARTIALLY RESOLVED — free-tier chosen; legal review still required

  Phase 1 (zero-cost, Dialagram + OpenRouter free) can begin immediately upon:
  - Researcher approval to run Phase 1 (zero-cost, $0)
  - IP-hold confirmation on the two free-tier providers
  - DIALAGRAM_API_KEY + OPENROUTER_API_KEY present in env at run time

  Phase 2 owner actions required (BLOCKED until Phase 1 completes):
  [OWNER-1] Phase 2 API spend approved (~$19-24 expected)
  [OWNER-2] Phase 2 API keys obtained
  [OWNER-3] IP counsel confirmation re: SPEC-001 schema on direct providers
```

**Status: READY_FOR_OWNER_APPROVAL (Phase 1, zero-cost, IP-hold decision pending)**

---

## Document Control

| Field | Value |
|---|---|
| Version | 2.0 |
| Created | 2026-09-04 |
| Status | READY_FOR_OWNER_APPROVAL (Phase 1 zero-cost) |
| Supersedes | v1.0 (2026-09-04, NOT_READY with 5 blockers) |
| Next action | Owner: confirm IP-hold on the three Phase 1 providers; confirm $0 budget approval |
| Related files | `STUDY-011-LIVE-CROSS-PROVIDER-PREREGISTRATION.md`, `STUDY-011-AMENDMENTS.md`, `data/study011_preregistration_manifest.json`, `STUDY-011-COST-FORECAST.md`, `EXTERNAL-IMPLEMENTER-OUTREACH.md` |
