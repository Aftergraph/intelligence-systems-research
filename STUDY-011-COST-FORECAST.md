# STUDY-011: Cost Forecast
## API Budget Estimation — Pre-Execution Planning Document

**Study:** STUDY-011 Cross-Provider Replication  
**Status:** DRAFT — Not yet approved for execution  
**Prepared:** 2026-09-04  
**Version:** 0.2 (revised post power-analysis)  

> [!CAUTION]
> This forecast must be recomputed after the final provider/model matrix is frozen and the power analysis is locked. Do not treat this as an approved budget. These are planning estimates only.

---

## 1. Final Sample Design (Power-Derived)

### Power Analysis Summary

| Parameter | Value | Justification |
|---|---|---|
| Smallest Effect of Interest (Cohen's h) | 0.50 | Conservative: 1/3 of STUDY-008 simulated effect (h=1.671). Below h=0.5, practical significance is questionable. |
| Target power | 80% | Standard minimum for confirmatory research |
| Per-hypothesis α | 0.01 | Specified in STUDY-011 protocol |
| Bonferroni correction | ÷ 3 (3 confirmatory hypotheses) | H1: FCR(A vs G), H2: VSR(C vs F), H3: tradeoff(A vs G cost) |
| Adjusted α | 0.00333 | Bonferroni-corrected |
| **Min N per cell (adjusted)** | **58 LIVE_VALID** | Computed via normal approximation to McNemar formula |

### Study Dimensions

```
PROVIDERS × CONDITIONS × MIN_LIVE_VALID_PER_CELL
= Planned LIVE_VALID target
/ Expected success rate (75%)
= Planned attempts
```

**Phase 1 — Zero-Cost (Dialagram + OpenRouter Free):**

| Dimension | Value |
|---|---|
| Provider strata | 2 (Dialagram/Nexum, OpenRouter free tier) |
| Confirmatory conditions | 4 (A, C, F, G) |
| Min LIVE_VALID per cell | 58 |
| **Total LIVE_VALID target** | **464** |
| Expected success rate | 75% |
| **Planned attempts** | **619** |

**Phase 2 — Paid (Pending Owner Approval):**

| Dimension | Value |
|---|---|
| Additional provider strata | 3 (OpenAI direct, Anthropic direct, Google direct) |
| Same conditions + N | 4 × 58 |
| **Additional LIVE_VALID target** | **696** |
| **Additional planned attempts** | **928** |

**Combined:**

| Metric | Value |
|---|---|
| Total provider strata | 5 |
| Total LIVE_VALID target | 1,160 |
| Total planned attempts | 1,547 |

> [!NOTE]
> The original STUDY-011 protocol stated "~400 runs" and "≥40 per cell." After power analysis with Bonferroni correction, the correct per-cell figure is **58 LIVE_VALID**. The 400-run estimate in the original document was inconsistent — it is superseded by this analysis.

---

## 2. Provider/Model Matrix (Frozen 2026-09-04)

### Tier 1 — Dialagram/Nexum (No New Paid API Required — Subscription Active)

**Auth:** via `DIALAGRAM_API_KEY` env var (runtime configuration only; never embedded).
**Retrieved at:** 2026-09-04T01:42:00Z
**Matrix SHA-256:** TBD at freeze  

| Model ID | Family | Tier Classification |
|---|---|---|
| `deepseek-v4` | DeepSeek (frontier) | STUDY-011 primary |
| `xiaomi-mimo-2.5` | MiMo (mid) | STUDY-011 primary |
| `qwen-3.8-max` | Qwen (frontier) | STUDY-011 primary (rate-limit caution) |
| `qwen-3.8-max-thinking` | Qwen (frontier + reasoning) | Exploratory |
| `tencent-hy3` | Tencent HY (mid) | Exploratory |
| `meta-muse-spark-1.3` | Meta Muse (mid) | Exploratory |
| `qwen-3.7-max` | Qwen (previous frontier) | Exploratory |

**Dialagram cost:** \$0.00 marginal (covered by \$5.50/week subscription)

### Tier 2 — OpenRouter Free Tier (No New Paid API Required)

**Auth:** via `OPENROUTER_API_KEY` env var (runtime configuration only; never embedded).
**Retrieved at:** 2026-09-04T01:42:00Z
**Free models identified:** 21 models  

Recommended for STUDY-011 Phase 1 (diverse model families, strong capabilities):

| Model ID | Family | Context | Notes |
|---|---|---|---|
| `google/gemma-4-31b-it:free` | Google Gemma 4 (mid-open) | 262K | Strong instruction following |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | NVIDIA Nemotron (large-open) | 1000K | 550B parameter — frontier-class |
| `nvidia/nemotron-3-super-120b-a12b:free` | NVIDIA Nemotron (mid-open) | 262K | 120B, MoE |
| `minimax/minimax-m3:free` | MiniMax M3 (frontier) | 1048K | Latest MiniMax |
| `z-ai/glm-5.2:free` | Z.AI GLM (mid-open) | 256K | Strong reasoning |
| `cohere/north-mini-code:free` | Cohere North (code-specialized) | 256K | Good for SWE workloads |
| `poolside/laguna-s-2.1:free` | Poolside Laguna (code) | 262K | Code-specialized |

**OpenRouter free cost:** \$0.00 (subject to OpenRouter rate limits on free tier)

> [!WARNING]
> OpenRouter free tier models have rate limits. Implement per-model concurrency caps and exponential backoff. Free tier may impose stricter limits than Dialagram. Test pacing before full run.

### Tier 3 — Direct Providers (Paid — Phase 2, Pending Owner Approval)

| Provider | Endpoint | Auth Required | Status |
|---|---|---|---|
| OpenAI | `api.openai.com/v1` | API key + billing | ❌ NOT OBTAINED |
| Anthropic | `api.anthropic.com/v1` | API key + billing | ❌ NOT OBTAINED |
| Google AI | `generativelanguage.googleapis.com/v1beta` | API key + billing | ❌ NOT OBTAINED |

---

## 3. Token Budget Estimation

### Per-Run Token Estimates

| Component | Estimate | Notes |
|---|---|---|
| Workload prompt (reduced, ≤2K tokens) | 1,500 tokens input | SWE-01 full prompt caused 429s — use shortened version |
| Mission contract overhead | 250 tokens input | SPEC-001 core payload |
| Model response (Cond A baseline) | 800 tokens output | Typical reasoning response |
| Verification call (Cond E/F/G) | 400 tokens input + 200 output | Assurance engine call |
| Recovery retry (Cond F/G) | 1,500 + 300 additional | On failure |
| **Total per LIVE_VALID run (avg Cond G)** | **~4,500 tokens** | Conservative estimate |

### Cost per 1K Tokens by Provider

| Provider | Input (\$/1K tok) | Output (\$/1K tok) | Model |
|---|---|---|---|
| Dialagram/Nexum | \$0.00 marginal | \$0.00 marginal | Subscription |
| OpenRouter free | \$0.00 | \$0.00 | Free tier |
| OpenAI (Phase 2) | ~\$0.0025 | ~\$0.010 | GPT-4o |
| Anthropic (Phase 2) | ~\$0.003 | ~\$0.015 | claude-opus-4 |
| Google (Phase 2) | ~\$0.00125 | ~\$0.005 | gemini-2.5-pro |

### Phase 1 Cost (Zero-Cost Providers)

| Category | Estimate |
|---|---|
| Dialagram (619 attempts × ~4.5K tok avg) | **\$0.00** (subscription) |
| OpenRouter free (supporting runs) | **\$0.00** |
| **Phase 1 Total** | **\$0.00 marginal** |

### Phase 2 Cost Estimate (Paid Providers — 928 Planned Attempts)

Per provider (928 attempts / 3 ≈ 310 attempts per provider):

| Provider | Input Cost | Output Cost | Subtotal (Expected) |
|---|---|---|---|
| OpenAI (GPT-4o) | 310×4.5K×\$0.0025 | 310×1K×\$0.010 | ~\$3.48 + \$3.10 = **\$6.58** |
| Anthropic (claude-opus-4) | 310×4.5K×\$0.003 | 310×1K×\$0.015 | ~\$4.19 + \$4.65 = **\$8.84** |
| Google (gemini-2.5-pro) | 310×4.5K×\$0.00125 | 310×1K×\$0.005 | ~\$1.74 + \$1.55 = **\$3.29** |

| Scenario | Phase 2 Total |
|---|---|
| Best case (all runs succeed, no retries) | ~\$10 |
| **Expected case** (~75% success, 25% retry overhead) | **~\$24** |
| Worst case (50% success, extensive retries, expensive models) | ~\$60 |

> [!IMPORTANT]
> The previous estimate of \$70–120 USD was based on an incorrect sample size of 400 total runs. The corrected Phase 2 design (928 paid attempts across 3 providers) costs significantly less: **~\$24 expected**. The prior estimate was conservatively wrong upward.

### Total Estimated API Spend

| Phase | Cost |
|---|---|
| Phase 1 (Dialagram + OpenRouter free) | **\$0.00** |
| Phase 2 (OpenAI + Anthropic + Google, pending approval) | **~\$24 expected (\$10–60 range)** |
| **Grand total** | **\$0–60 (expected: ~\$24)** |

---

## 4. Runtime Estimate

| Phase | Assumptions | Estimated Wall Time |
|---|---|---|
| Phase 1 (619 attempts, paced at 3 req/min/model) | ~200 min/model × 2 providers | ~7–10 hours total |
| Phase 2 (928 attempts, paced at 2 req/min/provider) | ~310 req × 3 providers | ~5–8 hours total |
| Analysis + reporting | Post-data | ~2 hours |
| **Total** | | **~15–20 hours** |

---

## 5. Rate-Limit Strategy

Based on STUDY-008 lessons (9 LIVE_PROVIDER_FAILURE from HTTP 429):

| Provider | Concurrency Cap | Base Delay | Backoff | Max Retries | Retry-After Compliance |
|---|---|---|---|---|---|
| Dialagram/Nexum | 1 req/model at a time | 5s inter-request | 2× up to 60s | 3 | Yes |
| OpenRouter free | 1 req/model at a time | 10s inter-request | 2× up to 120s | 3 | Yes |
| OpenAI direct | 3 parallel | 3s inter-request | 2× up to 60s | 3 | Yes |
| Anthropic direct | 2 parallel | 5s inter-request | 2× up to 60s | 3 | Yes |
| Google direct | 3 parallel | 3s inter-request | 2× up to 60s | 3 | Yes |

**Failed requests after max retries:** recorded as `LIVE_PROVIDER_FAILURE`. Never silently converted to simulation.

---

## 6. IP/Data-Transmission Status

| Transmission | Status | Notes |
|---|---|---|
| Sending workload prompts to Dialagram | ✅ Already occurring | Covered by existing subscription usage |
| Sending workload prompts to OpenRouter | ⚠️ PENDING | Workload prompts contain SPEC-001 mission schema. IP counsel review recommended before transmitting to OpenRouter/external providers |
| Sending to OpenAI/Anthropic/Google directly | ⚠️ PENDING | Same IP concern as above |
| Using non-sensitive/reduced benchmark prompts | ✅ Option available | Can use generic task prompts that don't expose proprietary SPEC-001 schema details |

> [!CAUTION]
> **Legal hold still active.** Before transmitting mission contract schema details to external providers, confirm with IP counsel whether such transmission is permitted under the current IP protection strategy. Generic task prompts (e.g., "fix this function") can be sent without exposing SPEC-001 internals.

---

## 7. Assumptions and Caveats

1. Token estimates assume shortened workload prompts (≤2K tokens). Full SWE-01 prompts caused HTTP 429 in STUDY-008.
2. Success rate of 75% is a planning assumption. Actual rate from STUDY-008 (Dialagram): 2/11 = 18% LIVE_VALID (but primarily due to harness bug, not provider failures). After fixing the harness, 75% is reasonable for well-paced requests.
3. OpenRouter free tier models may impose stricter rate limits than documented. Test pacing on a 5-run pilot before full Phase 1 execution.
4. Pricing for Phase 2 providers is from public pricing pages as of 2026-09. Prices may change.
5. This document does not constitute approval to spend. Owner approval required before Phase 2 execution.

---

## Document Control

| Field | Value |
|---|---|
| Version | 0.2 |
| Created | 2026-09-04 |
| Power analysis script | `scripts/study011_power_analysis.py` |
| OpenRouter catalog | `data/openrouter_model_catalog.json` |
| Status | DRAFT — Awaiting owner approval for Phase 2 |
