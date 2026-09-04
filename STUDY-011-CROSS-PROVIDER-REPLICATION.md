# STUDY-011: Cross-Provider Replication Protocol (v0.3 — Protocol Integrity Revision)
## The Next Major Empirical Gate Toward Level D

**Study ID:** STUDY-011  
**Program:** Jonas Abde Intelligence Systems Research Program Q3 2026  
**Status:** PLANNED — Not Yet Executed  
**Version:** 0.3 (Protocol Integrity Revision — 2026-09-04)  
**Authors:** Jonas Abde  
**Classification:** PROTOCOL DOCUMENT (No empirical data collected yet)

> [!IMPORTANT]
> STUDY-011 is the next major empirical gate toward Level D — not the single gate. Level D still requires, at minimum: defensible live model evidence, frozen implementable specification, normative conformance, genuinely external blind implementation, cross-runtime interoperability, and defensible security validation. External reproduction is independently required.

---

## 1. Context: STUDY-008 Reclassification

STUDY-008 is correctly classified as: **Live Benchmark Pilot / Harness Validation with Simulation-Supported Secondary Results.**

Its execution accounting is definitive:
- 275 attempted runs
- **2 LIVE_VALID** (deepseek-v4, xiaomi-mimo-2.5 on SWE-01)
- **9 LIVE_PROVIDER_FAILURE** (HTTP 429 rate limiting on SWE-01 full prompt)
- **264 SIMULATED** (harness bug: `is_live_call = (idx == 0)`)

STUDY-008 is **not** a completed inferential live model benchmark. Its primary scientific contribution is methodological: the provenance and audit mechanisms correctly detected and classified the live/simulation defect. This is a valid and important systems result — the audit trail worked.

---

## 2. Corrected Level-D Requirements

Level D (Implementable Standard Candidate) requires ALL of the following:

| Requirement | Current State |
|---|---|
| Defensible live model evidence (STUDY-011) | ❌ Not yet |
| Frozen implementable specification (SPEC-001 v0.2) | ✅ Exists |
| Normative conformance (14/14 across 3 in-tree implementations) | ✅ Exists |
| Genuinely external blind implementation | ❌ Not yet |
| Cross-runtime interoperability evidence | ⚠️ In-tree only |
| Defensible security validation | ⚠️ Internally tested |

No single study or action alone unlocks Level D.

---

## 3. Confirmatory Hypotheses (Pre-Stated)

Three primary confirmatory hypotheses only. Everything else is exploratory.

**H1 — FCR Reduction (Evidence Gating):**  
Evidence gating (Condition G) produces a statistically and practically significant reduction in False Completion Rate compared to the native agent (Condition A), replicated across ≥ 2 provider strata.

**H2 — VSR Recovery (Evidence-Triggered Recovery vs Blind Retries):**  
Evidence-triggered recovery (Condition F) produces higher Verified Success Rate than blind retries (Condition C) in the same workload set, replicated across ≥ 2 provider strata.

**H3 — Cost/Reliability Tradeoff:**  
The full runtime (Condition G) produces an acceptable Cost Per Verified Outcome relative to the native baseline (Condition A), defined as CPVO(G) ≤ 2.0 × CPVO(A) while maintaining FCR(G) ≤ 0.05.

**Stopping rule for failed replication:**  
If the direction of H1 or H2 is reversed (FCR(G) > FCR(A) or VSR(F) < VSR(C)) within any provider stratum, that stratum is classified as `REVERSED` and must be investigated before advancing any maturity claim.

---

## 4. Replication Gate Criteria (Defined Pre-Execution)

For each confirmatory hypothesis, define the threshold before data collection:

| Outcome | Definition |
|---|---|
| `SUPPORTED` | Effect direction correct, magnitude ≥ SEOI (h=0.5), p ≤ adjusted-α, in ≥ 2 strata |
| `PARTIALLY_SUPPORTED` | Effect direction correct, magnitude < SEOI or p > adjusted-α, or only 1 stratum |
| `FAILED_TO_REPLICATE` | Effect direction correct but not significant and magnitude negligible in all strata |
| `REVERSED` | Effect direction opposite to hypothesis in ≥ 1 stratum |

The gate for Level D progress requires: H1 = `SUPPORTED` and H2 = `SUPPORTED`.

---

## 5. Study Design

### 5.1 Confirmatory Conditions (4 only)

| Condition | Description | Hypothesis Role |
|---|---|---|
| **A** | Native agent, no mission contract, no evidence gating | Baseline for H1, H3 |
| **C** | Native agent + blind retries (no evidence gating) | Baseline for H2 |
| **F** | Evidence gate + evidence-triggered recovery | Treatment for H2 |
| **G** | Full runtime: mission contract + authority + budgets + evidence gate + recovery + routing | Treatment for H1, H3 |

All other conditions (B, D, E, ablations) are **exploratory** if run.

### 5.2 Power Analysis (Formal)

| Parameter | Value | Justification |
|---|---|---|
| Smallest Effect of Interest (SEOI) | Cohen's h = 0.50 | Conservative: ≈1/3 of STUDY-008 simulated h=1.671. Below h=0.5, practical significance is doubtful. |
| Target power | 80% | Standard minimum |
| Per-hypothesis α | 0.01 | Specified in protocol |
| Bonferroni correction | ÷ 3 hypotheses | H1, H2, H3 |
| Adjusted α | 0.00333 | |
| **Min LIVE_VALID per cell** | **58** | Computed via normal approximation to McNemar formula |

**Formula:**  
$$N_{cell} = \left\lceil \frac{(z_{1-\alpha_{\text{adj}}/2} + z_{1-\beta})^2}{h^2} \right\rceil = 58$$

Script: `scripts/study011_power_analysis.py`

### 5.3 Provider Strata

| Phase | Provider | Type | Cost |
|---|---|---|---|
| **Phase 1** | Dialagram/Nexum | Routed multi-model (subscription) | \$0 marginal |
| **Phase 1** | OpenRouter free tier | Routed multi-model (free) | \$0 |
| Phase 2 (pending) | OpenAI direct | Direct provider | ~\$7 |
| Phase 2 (pending) | Anthropic direct | Direct provider | ~\$9 |
| Phase 2 (pending) | Google AI direct | Direct provider | ~\$3 |

> Dialagram and OpenRouter each count as **one provider/control-plane stratum** regardless of how many underlying model families they expose.

### 5.4 Sample Size Summary

```
Phase 1 (zero-cost):
  4 conditions × 2 provider strata × 58 LIVE_VALID = 464 LIVE_VALID target
  / 75% success rate assumption = 619 planned attempts

Phase 2 (paid, pending):
  4 conditions × 3 provider strata × 58 LIVE_VALID = 696 LIVE_VALID target
  / 75% = 928 planned attempts

Combined: 1,160 LIVE_VALID target / 1,547 planned attempts
```

### 5.5 Workload Set

- **Domain:** Software Engineering (SWE), abbreviated to ≤2,000 token prompts
- **Rationale for length reduction:** Full SWE-01 prompt caused HTTP 429 in STUDY-008. Shortened prompts preserve task semantics while respecting rate limits.
- **Workload set:** Frozen in STUDY-011-PREREGISTRATION.md before first live run
- **Failure injection:** 10 modes from STUDY-008 protocol retained

---

## 6. Execution Mode: LIVE_ONLY

The STUDY-011 harness (`run_study_011.py`, not yet written) MUST implement explicit execution modes:

```python
class ExecutionMode(Enum):
    LIVE_ONLY = "LIVE_ONLY"
    SIMULATION_ONLY = "SIMULATION_ONLY"
    DRY_RUN = "DRY_RUN"
```

For STUDY-011 confirmatory runs: `mode = ExecutionMode.LIVE_ONLY`

**Invariant (hard rejection):**
```python
if study_id == "STUDY-011" and run.execution_class != "LIVE":
    raise RuntimeError(
        f"INVARIANT VIOLATION: STUDY-011 requires LIVE execution. "
        f"Got {run.execution_class!r} for run {run.run_id!r}. "
        "Rejecting from confirmatory dataset. No simulation fallback permitted."
    )
```

**No silent fallback.** If the remote request cannot execute → record `LIVE_PROVIDER_FAILURE`. Never convert to simulation.

---

## 7. Per-Run Provenance Requirements

Every LIVE_VALID run must contain ALL of the following (else classification ≠ LIVE_VALID):

```
run_id                      # UUID: study011-{provider}-{condition}-{workload}-{replica}
study_id                    # "STUDY-011"
provider_name               # "dialagram", "openrouter", "openai", "anthropic", "google"
exact_model_id              # as returned by provider API
provider_request_id         # provider-assigned ID where available
http_status                 # e.g. 200, 429, 504
request_timestamp_utc       # ISO 8601
response_timestamp_utc      # ISO 8601
latency_ms                  # response - request in ms
request_hash                # SHA-256 of serialized request payload
response_hash               # SHA-256 of raw response body
mission_hash                # SHA-256 of frozen mission contract
token_count_prompt          # from provider usage metadata
token_count_completion      # from provider usage metadata
cost_usd                    # computed from token counts × provider rate
is_live                     # MUST be True; False → EXCLUDED with alert
execution_class             # LIVE_VALID | LIVE_PROVIDER_FAILURE | EXCLUDED
condition                   # A | C | F | G
workload_id                 # from frozen workload set
mission_state_final         # VERIFIED | FAILED | TIMEOUT | ERROR
fcr_flag                    # bool: VERIFIED without valid Tier-2 receipt
vsr_flag                    # bool: VERIFIED with valid Tier-2 receipt
raw_response_excerpt        # first 500 chars (full in separate file)
manifest_hash               # master run manifest SHA-256 at time of run
```

---

## 8. Statistical Analysis Plan

**Primary binary outcomes:** FCR, VSR (per run, per cell)

**Methods:**
- Within-provider McNemar test (paired by workload) for H1 and H2
- Mixed-effects logistic regression: outcome ~ condition + provider + model + (1|workload)
- Bonferroni correction applied across 3 confirmatory hypotheses
- Effect size: Cohen's h (binary outcomes)
- 95% Wilson confidence intervals on all proportions

**Factors:**
- Fixed: condition (A/C/F/G), provider stratum
- Random: workload (blocking factor)
- Interaction: condition × provider (to test consistency across strata)

**Reporting requirements:**
- Raw counts per cell
- Effect size with 95% CI
- Adjusted p-values
- Provider-level breakdown (no collapsing across strata without justification)
- Separate reporting of attempt success rate, LIVE_VALID rate, LIVE_PROVIDER_FAILURE rate

**Not acceptable:** reporting only p < 0.05 without model structure, effect size, or CI.

---

## 9. Provider/Model Matrix (To Be Frozen Before First Run)

Immediately before execution, resolve from provider APIs and freeze:

| Field | Required |
|---|---|
| provider | exact name |
| exact_model_id | as returned by API |
| api_version | endpoint version |
| retrieved_at | ISO 8601 |
| input_pricing | \$/token |
| output_pricing | \$/token |
| context_window | tokens |
| tool_support | bool |
| reasoning_capability | bool |
| deprecation_status | active/deprecated |

SHA-256 the frozen matrix file. No model substitution after data collection begins.

**Protocol deviation procedure:** If provider retires a model mid-study, document as `PROTOCOL_DEVIATION_001` in `STUDY-011-AMENDMENTS.md`. Do not silently substitute.

---

## 10. Rate-Limit Strategy

Based on STUDY-008 LIVE_PROVIDER_FAILURE root cause (HTTP 429 on SWE-01 full prompt):

| Provider | Max Concurrency | Min Inter-Request Delay | Backoff | Max Retries | Retry-After |
|---|---|---|---|---|---|
| Dialagram/Nexum | 1 | 5s | 2× → 60s | 3 | Yes |
| OpenRouter free | 1 | 10s | 2× → 120s | 3 | Yes |
| OpenAI direct | 3 | 3s | 2× → 60s | 3 | Yes |
| Anthropic direct | 2 | 5s | 2× → 60s | 3 | Yes |
| Google direct | 3 | 3s | 2× → 60s | 3 | Yes |

Provider failure types are data. Report separately:
- 429 Too Many Requests
- 5xx server errors
- Connection timeout
- Malformed output
- Context-length exceeded
- Provider refusal

---

## 11. Cross-Provider Independence Statement

STUDY-011 correctly distinguishes:

| Concept | This Study |
|---|---|
| Model diversity | Multiple underlying model families per stratum |
| Provider/control-plane diversity | Each stratum (Dialagram, OpenRouter, OpenAI, Anthropic, Google) is one provider/control-plane |
| Provider independence | Dialagram + OpenRouter = 2 strata (but both are routed gateways); OpenAI + Anthropic + Google = 3 direct strata |

For Level D claims, the most valuable evidence comes from **direct provider strata** (Phase 2), not gateway strata.

---

## 12. Preregistration Process

Before the first live outcome is observed:

1. Finalize this document (STUDY-011-CROSS-PROVIDER-REPLICATION.md v1.0)
2. Create frozen workload set file
3. Create frozen provider/model matrix file
4. Create analysis script (`scripts/study011_analyze.py`)
5. Create `STUDY-011-LIVE-CROSS-PROVIDER-PREREGISTRATION.md` containing all of the above
6. Compute SHA-256 of preregistration document
7. Record `freeze_timestamp` and commit
8. Record `first_live_run_timestamp` when first attempt executes

Any post-freeze change → `STUDY-011-AMENDMENTS.md` entry with rationale. Not an invisible edit.

---

## 13. Remaining Blockers

| Blocker | Status | Owner |
|---|---|---|
| STUDY-011 harness (`run_study_011.py`) written | ❌ NOT WRITTEN | Program |
| LIVE_ONLY mode invariant implemented | ❌ NOT IMPLEMENTED | Program |
| Workload set frozen (≤2K token versions) | ❌ NOT FROZEN | Program |
| Provider/model matrix frozen with SHA-256 | ❌ NOT FROZEN | Program |
| Analysis script (`study011_analyze.py`) written | ❌ NOT WRITTEN | Program |
| Pre-registration document created + SHA-256 | ❌ NOT CREATED | Program |
| IP counsel confirmation re: workload transmission to external APIs | ❌ PENDING | Researcher |
| Phase 2 API keys (OpenAI, Anthropic, Google) | ❌ NOT OBTAINED | Researcher |
| Phase 2 budget approved (~\$24 expected) | ❌ PENDING | Researcher |
| OpenRouter free tier rate-limit pilot (5 runs) | ❌ NOT DONE | Program |

---

## 14. Document Control

| Field | Value |
|---|---|
| Version | 0.3 |
| Created | 2026-09-04 |
| Status | DRAFT PROTOCOL v0.3 (Protocol Integrity Revision) |
| Supersedes | v0.2 (2026-09-04) |
| SHA-256 | TBD at freeze |
| Power analysis | `scripts/study011_power_analysis.py` |
| Cost forecast | `STUDY-011-COST-FORECAST.md` |
