# STUDY-008: Live MISSION-Bench Evaluation v2 — Preregistration Protocol

**Research Program:** Jonas Abde Intelligence Systems Research Program — Q3 2026  
**Document ID:** `STUDY-008-LIVE-v2-PREREG`  
**Protocol Version:** `v2.0-FROZEN`  
**Status:** **PREREGISTERED-DRAFT** (pending owner approval)  
**Registration Date:** 2026-09-04  
**Principal Investigator:** Jonas Abde  

---

## 0. Context: G-S0 Closure and Track A Execution

G-S0 (STUDY-011 scientific closure: commits 5cf5d29→34f2d14) is **CLOSED**. Track A (MISSION-Bench Live) is now active per `docs/CANONICAL-RESEARCH-ROADMAP-v2.md` §1.

This preregistration implements Track A v2: live workloads under real fault injection, with frozen metrics and integrity invariants carried forward from STUDY-011.

**Non-pooling declaration:** STUDY-008-v2 data is **never pooled** with STUDY-011 or STUDY-008-v1 datasets. Analysis remains stratum-specific; pooled results are exploratory only.

---

## 1. Hypotheses (Frozen)

| ID | Hypothesis | Test |
|---|---|---|
| H1 (FCR Reduction) | Evidence-gated conditions (F, G) achieve `FCR ≤ 5.0%` vs baseline (A) `FCR ≥ 25.0%` | McNemar, α = 0.01 |
| H2 (Recovery Superiority) | Condition F achieves higher VSR than C (blind retries) with `OR ≥ 2.5` | McNemar, α = 0.01 |
| H3 (CPVO Inversion) | Despite control-plane overhead, G reduces CPVO by `≥ 50%` vs A in failure-prone runs | Wilcoxon, α = 0.01 |
| H4 (Unauthorized Action Rate) | Condition G achieves `UAR = 0` across all runs | Binomial exact, 95% Wilson CI |
| H5 (Recovery Correctness) | ≥90% of recovery attempts produce `VERIFIED` state without unauthorized tool calls | Binomial exact, 95% Wilson CI |

---

## 2. Experimental Conditions

| Condition ID | Mission Contract | Verification Gate | Recovery Loop | Authority/Budget |
|---|---|---|---|---|
| **A** | None | Self-Reported | None | None |
| **C** | Prompt Only | Self-Reported | Fixed Loop (3 retries) | None |
| **F** | SPEC-001 | Deterministic Verifier | Diagnostic State Recovery | None |
| **G** | SPEC-001 | Logical Assurance Boundary | Diagnostic State Recovery | Enforced |

**Targeted Ablations (G):**
- `G-no-auth`: No authority delegation checks
- `G-no-evid`: Stochastic self-checks instead of deterministic verifiers
- `G-no-rec`: Terminate on first verification failure
- `G-no-state`: In-memory state only (no journal replay)
- `G-no-prog`: Monolithic YAML manifests instead of progressive disclosure

---

## 3. Workload Design & Fault Injection

### Frozen Workload Set
- **25 standardized benchmark tasks** across 5 operational domains (SWE, SRE, DE, RES, OPS)
- Each task has nominal and failure-injected variants

### Fault Injection Matrix
| Fault Code | Description | Target Condition Impact |
|---|---|---|
| `FAIL-TOOL` | Tool execution timeout or non-zero exit code | All |
| `FAIL-NET` | Provider transient rate-limit (429) or gateway error (5xx) | A, C, F, G |
| `FAIL-LATENCY` | Latency spike (>10s) injected at random tool call | F, G |
| `FAIL-MALFORMED` | Provider returns malformed JSON response | A, C, F, G |
| `FAIL-STALE` | Environment state modified outside agent context | All |
| `FAIL-HALLUC` | Agent emits non-existent file path or invalid parameters | All |
| `FAIL-MID-MISSION` | Mid-mission crash + resume (checkpoint reload) | F, G only |
| `FAIL-REVOKE` | Delegation authority token expired/revoked mid-run | G |

---

## 4. Live Model Matrix & Provider Stratification

### Provider/Model Strata (Phase 1)
| Stratum | Provider | Exact Model ID | Model Family | Context | Pricing |
|---|---|---|---|---|---|
| **S1** | Dialagram / Nexum | `qwen-3.8-max` | Qwen/Alibaba | 256k | Flat ($5.50/wk) |
| **S1** | Dialagram / Nexum | `deepseek-v4` | DeepSeek AI | 128k | Flat ($5.50/wk) |
| **S1** | Dialagram / Nexum | `xiaomi-mimo-2.5` | Xiaomi MiMo | 64k | Flat ($5.50/wk) |
| **S2** | OpenRouter | `google/gemma-2b-it:free` | Google Gemma | 8k | Free |
| **S2** | OpenRouter | `z-ai/glm-4:free` | Z-AI GLM | 128k | Free |

**Note:** Phase 1 includes ≥3 models (≥2 providers), with at least one small/open model (`gemma-2b-it:free`).

**Model Freeze:** 2026-09-04T00:00:00Z. No silent parameter substitutions permitted.

---

## 5. Metrics & Frozen Thresholds

### Primary Metrics (Frozen Thresholds)
| Metric | Formula | Success Threshold | Failure Threshold |
|---|---|---|---|
| **VSR** (Verified Success Rate) | `verified_runs / total_runs` | ≥70% | <50% |
| **FCR** (False Completion Rate) | `claimed_complete_but_failed / claimed_complete` | ≤5% | ≥25% |
| **UAR** (Unauthorized Action Rate) | `unauthorized_calls / total_calls` | 0 | >0 |

### Secondary Metrics (No Thresholds — Reporting Only)
- **CPVO** (Cost Per Verified Outcome): `total_cost / verified_outcomes`
- **CPT** (Control Plane Tax): `orchestrator_tokens / total_tokens`
- **Recovery Correctness**: `successful_recoveries / recovery_attempts`
- **Time to Verified Outcome (TVO)**: p50 and p90 latency

---

## 6. Scoring & Evidence Rules

### Automated Scoring
- **Only frozen workload validators** produce ground truth (e.g., `test_*.py`, manifest checksums)
- **No LLM-judge** scoring without inter-rater validation (2+ independent validators, Kappa ≥0.8)
- Run manifests: `schemas/evidence.v0alpha1.json` with SHA-256 hashes

### Evidence Classes (LIVE_ONLY Invariant)
| Class | Description | Denominator Count? |
|---|---|---|
| `LIVE_VALID` | Genuine remote call, valid response, manifest_hash matches | Yes |
| `LIVE_PROVIDER_FAILURE` | Transient upstream issue (429, 5xx, timeout, malformed JSON) | Yes (denominator only) |
| `LIVE_PROTOCOL_FAILURE` | Harness contract violation (malformed response shape) | Yes (denominator only) |
| `INVALID_PROTOCOL` | Missing required fields (is_live, http_status, provider_request_id) | No |
| `EXCLUDED` | is_live=False or execution_class=SIMULATED in confirmatory conditions | No |

**Pre-registered exclusions:**
1. `request_hash` does not match SHA-256 of payload sent
2. `provider_request_id` <8 chars or matches `^(0+|test|debug)$`
3. Paired runs have different `manifest_hash` (workload drift)
4. Same `replicate_id` hit more than once per cell

---

## 7. Attempt Ceilings & Stopping Rules

### Per-Cell Rules
- **Planned maximum attempts:** 60 (20 workloads × 3 replicates)
- **LIVE_VALID target:** 58 per cell (4 cond × 2 strata × 58 = 464 total floor)
- **Attempt ceiling:** 619 (worst case including provider failures)
- **Stopping condition:** Every cell reaches 58 LIVE_VALID OR 619 attempts reached

### Per-Run Rules
A run terminates if:
1. Verified completion achieved
2. Maximum turns reached (`T_max = 5`)
3. Mission budget exhausted
4. Irreversible error encountered
5. Human operator cancellation

### Exclusion Rules
Runs excluded only for local infrastructure power failure or OS abort. Rate-limits, network drops, model formatting failures are **retained** as operational failures.

---

## 8. Statistical Analysis Plan

1. **Paired Comparisons:** McNemar test (two-tailed, continuity correction) on discordant pairs
2. **Continuous Distributions:** Wilcoxon signed-rank test (non-parametric)
3. **Confidence Intervals:** 95% Wilson score intervals for all rates
4. **Effect Sizes:** Cohen's h for proportions, Cohen's d / Cliff's delta for continuous
5. **Multiplicity Correction:** Benjamini-Hochberg FDR (α = 0.05) for exploratory analyses; Bonferroni (α = 0.0033) for primary H1 (3 tests)

---

## 9. Freeze Manifest (Phase 1)

| Artifact | Path | SHA-256 |
|---|---|---|
| Workload manifest | `data/study008_v2_workload_manifest.json` | (computed at freeze) |
| Provider/model matrix | `data/study008_v2_provider_model_matrix.json` | (computed at freeze) |
| Analysis script | `experiments/live_benchmark/study008_v2_analyze.py` | (computed at freeze) |
| Harness | `experiments/live_benchmark/run_study_008_v2.py` | (computed at freeze) |
| Analysis test suite | `tests/test_study008_v2_analyze.py` | (computed at freeze) |
| This document | `STUDY-008-LIVE-v2-PREREGISTRATION.md` | (computed at freeze) |

---

## 10. Stopping / Go-No-Go Decision

- **Execution start:** Requires owner approval and status `READY_FOR_OWNER_APPROVAL`
- **Phase 1 (free models):** Proceed with 2 strata, 5 models total
- **Phase 2 (paid providers):** Requires separate preregistration amendment (legal hold lift)

---

## 11. Limitations (Pre-Declared)

- **N per cell = 58** is below optimal Bonferroni-adjusted power; Phase 1 reports effect sizes + exact CIs, does not claim null results below detectable threshold
- **Two provider strata** both routed gateways (Dialagram, OpenRouter); "provider independence" claim weaker than direct-API Phase 2
- **No external blinded scorer** in Phase 1 (internal only)

---

## 12. Change Control

Post-freeze changes require numbered `PROTOCOL_AMENDMENT_NNN` entries in `STUDY-008-AMENDMENTS.md` with trigger event, exact diff, before/after SHA-256, justification, and timestamp. Amendments are frozen at append-time.

**Version:** 2.0-FROZEN  
**Freeze Timestamp (UTC):** 2026-09-04T00:00:00Z  
**Classification:** PROTOCOL FREEZE (no post-hoc editing without PROTOCOL_AMENDMENT)
