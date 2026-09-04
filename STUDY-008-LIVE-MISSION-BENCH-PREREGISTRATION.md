# STUDY-008: Live Model MISSION-Bench Evaluation — Preregistration Protocol
**Research Program:** Jonas Abde Intelligence Systems Research Program — Q3 2026  
**Document ID:** `STUDY-008-PREREG`  
**Protocol Version:** `v1.0-FROZEN`  
**Registration Date:** 2026-09-04  
**Principal Investigator:** Jonas Abde  
**Status:** **FROZEN PRIOR TO OUTCOME ANALYSIS**  

---

## 1. Executive Summary & Research Questions

Prior evaluations in this program (STUDY-002, STUDY-005) demonstrated significant reductions in False Completion Rate (FCR) and Cost Per Verified Outcome (CPVO) within deterministic simulated environments. To advance program maturity from **Level C+ / Provisional-D** toward defensible international standardization, this study executes the first **live, multi-model empirical benchmark** utilizing actual remote API executions across distinct model families.

### Research Questions
- **RQ1 (Evidence Gating under Stochasticity):** Does deterministic evidence gating significantly reduce False Completion Rate (FCR) compared to unconstrained self-reporting (Condition A), prompted criteria (Condition B), and LLM-as-a-Judge (Condition D) when models operate with non-zero stochastic temperature ($T = 0.2$)?
- **RQ2 (Causal Role of Recovery):** Does evidence-gated recovery (Condition F/G) produce a statistically significant increase in Verified Success Rate (VSR) compared to unguided retries (Condition C) across realistic failure-injected tasks?
- **RQ3 (Control Plane Economics):** Does the Control Plane Tax (orchestration latency and token overhead) introduced by SPEC-001 result in a lower net Cost Per Verified Outcome (CPVO) due to the prevention of wasted execution and false completion loops?
- **RQ4 (Model Heterogeneity vs. Routing):** Does Policy-Constrained Scored Routing dynamically select models to achieve equivalent or superior VSR at lower cost compared to static frontier model assignments?
- **RQ5 (Constraint Retention under Pressure):** Does segregated pinned control context maintain higher constraint retention than monolithic prompt expansion across heterogeneous model context windows?

---

## 2. Hypotheses (Frozen)

- **H1 (FCR Reduction):** Deterministic evidence gating (Conditions E, F, G) will achieve $\text{FCR} \le 5.0\%$ across all live model families, whereas Conditions A, B, and D will exhibit $\text{FCR} \ge 25.0\%$ ($p < 0.001$, McNemar test).
- **H2 (Recovery Superiority over Blind Retry):** Condition F (Evidence Gate + Recovery) will achieve a higher VSR than Condition C (Blind Retries) with an odds ratio $\text{OR} \ge 2.5$ ($p < 0.01$).
- **H3 (CPVO Economic Inversion):** Despite non-zero control plane token overhead ($\le 250$ tokens core payload), Condition G will reduce CPVO by $\ge 50\%$ compared to Condition A in failure-prone environments ($p < 0.01$, Wilcoxon signed-rank test).
- **H4 (Router Efficiency):** Policy-Constrained Scored Routing will achieve $\ge 90\%$ of the frontier model's VSR while reducing total token expenditure by $\ge 35\%$.
- **H5 (Assurance Resilience):** Zero agent-generated counterfeit evidence receipts will be accepted by `AssurancePrincipal` under Condition G ($0\%$ compromise rate).

---

## 3. Experimental Conditions

The benchmark evaluates 7 primary conditions and 5 targeted ablations:

| Condition ID | Description | Mission Contract | Verification Gate | Recovery Loop | Authority / Budget |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Condition A** | Native Agent Baseline | None | Self-Reported (Model Claim) | None | None |
| **Condition B** | Native + Acceptance Prompt | Prompt Text Only | Self-Reported (Model Claim) | None | None |
| **Condition C** | Native + Blind Retries | Prompt Text Only | Self-Reported (Model Claim) | Fixed Loop (up to 3 retries) | None |
| **Condition D** | LLM-as-a-Judge | Prompt Text Only | Secondary Model Review | None | None |
| **Condition E** | Evidence-Gated One-Shot | SPEC-001 | Deterministic Verifier (Tier 2) | None (Terminal on Fail) | None |
| **Condition F** | Evidence-Gated + Recovery | SPEC-001 | Deterministic Verifier (Tier 2) | Diagnostic State Recovery | None |
| **Condition G** | Full Intelligence Runtime | SPEC-001 | Logical Assurance Boundary | Diagnostic State Recovery | Enforced (RLock & RFC 8693) |

### Targeted Ablations of Condition G:
- **G-no-auth:** Full runtime without authority delegation checks (unbounded tool access).
- **G-no-evid:** Full runtime substituting deterministic verifiers with stochastic model self-checks.
- **G-no-rec:** Full runtime terminating immediately upon first verification failure.
- **G-no-state:** Full runtime executing without durable journal replay (in-memory state only).
- **G-no-prog:** Full runtime injecting monolithic YAML manifests instead of progressive disclosure.

---

## 4. Workload Design & Task Families

Workloads comprise **25 standardized benchmark tasks** distributed across 5 diverse operational domains, each evaluated across nominal and failure-injected variants:

1. **Software Engineering (SWE):**
   - Repository patch application, unit test failure remediation, dependency lockfile resolution, boundary condition bug repair.
2. **DevOps & Site Reliability Engineering (SRE):**
   - Configuration reconciliation, Prometheus metric anomaly diagnosis, Kubernetes deployment rolling updates, pod incident remediation.
3. **Data Engineering (DE):**
   - DuckDB schema transformation, corrupt CSV ingest validation, missing value imputation, multi-table reconciliation.
4. **Research & Information Work (RES):**
   - Multi-document constraint synthesis, provenance citation validation, factual inconsistency detection, structured report generation.
5. **Agent Operations & Tool Orchestration (OPS):**
   - Multi-step file manipulation, bounded subdelegation workflow, quota exhaustion mitigation, authorization renewal.

### Injected Failure Modes (Fault Matrix):
- `FAIL-TOOL`: Synthetic tool execution timeout or exit code non-zero.
- `FAIL-NET`: Provider transient rate-limiting or HTTP 502 gateway error.
- `FAIL-STALE`: Environment state modified concurrently outside agent context.
- `FAIL-HALLUC`: Model emits non-existent file path or invalid parameters.
- `FAIL-PRESSURE`: Context window compressed beyond 75% capacity.
- `FAIL-REVOKE`: Delegation authority token expired or revoked mid-run.
- `FAIL-BUDGET`: Token ceiling reached during multi-turn iteration.
- `FAIL-PARTIAL`: Side effect executed remotely before uncommitted failure.
- `FAIL-VERIF`: Test fixture initially fails due to simulated regression.
- `FAIL-REC-EXH`: Multi-turn recovery budget exhausted.

---

## 5. Live Model Matrix & Provider Stratification

### Strict Terminology Distinction:
- **Live Multi-Model:** Independent model families (architectures, training pipelines, weights) evaluated simultaneously.
- **Live Multi-Provider:** Heterogeneous API provider control planes and physical routing gateways.

| Tier | Provider / Gateway | Exact Model Identifier | Model Family | Context Limit | Pricing (In/Out $/1M) | Tool Support |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1 (Multi-Model Router)** | Dialagram / Nexum | `qwen-3.8-max` | Qwen / Alibaba | 256,000 | Flat ($5.50/wk) | Yes |
| **Tier 1 (Multi-Model Router)** | Dialagram / Nexum | `deepseek-v4` | DeepSeek AI | 128,000 | Flat ($5.50/wk) | Yes |
| **Tier 1 (Multi-Model Router)** | Dialagram / Nexum | `xiaomi-mimo-2.5` | Xiaomi MiMo | 64,000 | Flat ($5.50/wk) | Yes |
| **Tier 1 (Multi-Model Router)** | Dialagram / Nexum | `tencent-hy3` | Tencent Hunyuan | 128,000 | Flat ($5.50/wk) | Yes |
| **Tier 2 (Frontier Direct API)** | Direct OpenAI / Anthropic | `gpt-4o` / `claude-3-7-sonnet` | OpenAI / Anthropic | 128k / 200k | Standard API | Yes |
| **Tier 3 (Local / Open-Weight)** | Local Ollama / vLLM | `qwen2.5-coder:7b` | Open Qwen Coder | 32,768 | $0.00 (Local) | Yes |

*Model freeze timestamp: 2026-09-04T00:00:00Z. No silent model parameter substitutions permitted.*

---

## 6. Run Provenance Specification

Every single live run generates an immutable JSON record adhering to schema `schemas/evidence.v0alpha1.json` and sealed with a cryptographic hash:
```json
{
  "experiment_id": "STUDY-008-LIVE",
  "run_id": "run-G-swe-01-94812",
  "condition": "G",
  "workload_id": "SWE-01",
  "provider": "dialagram",
  "exact_model_id": "qwen-3.8-max",
  "timestamp_iso": "2026-09-04T01:15:00Z",
  "hashes": {
    "system_prompt_sha256": "...",
    "mission_contract_sha256": "...",
    "request_parameters_sha256": "..."
  },
  "raw_response": "...",
  "tool_calls": [],
  "tool_responses": [],
  "routing_receipt": {},
  "authority_receipts": [],
  "budget_reservations": [],
  "assurance_receipts": [],
  "verifier_output": {},
  "ground_truth": {},
  "usage": {
    "input_tokens": 412,
    "output_tokens": 128,
    "total_tokens": 540,
    "latency_ms": 1420.5,
    "cost_usd": 0.0012
  },
  "final_mission_state": "VERIFIED",
  "manifest_sha256": "..."
}
```
All run manifests are indexed in `data/live_run_manifest.json` with a root SHA-256 hash over the entire dataset.

---

## 7. Primary & Secondary Metrics

### Primary Metrics:
1. **Verified Success Rate (VSR):** $\frac{\text{Runs with } \text{State} = \text{VERIFIED} \land \text{Ground Truth Valid}}{\text{Total Runs}}$
2. **False Completion Rate (FCR):** $\frac{\text{Runs Reported Complete by Agent/Judge but Ground Truth Fails}}{\text{Total Runs Claiming Completion}}$

### Secondary Metrics:
3. **Task Success Rate (TSR):** Raw rate of achieving functional outcome regardless of formal verification.
4. **Constraint Retention Rate (CRR):** Percentage of active mission constraints adhered to across all tool dispatches.
5. **Cost Per Verified Outcome (CPVO):** $\frac{\sum \text{Total Cost of All Runs}}{\text{Count of Truly Verified Outcomes}}$
6. **Time to Verified Outcome (TVO):** Mean and $p90$ latency for runs reaching `VERIFIED`.
7. **Control Plane Tax (CPT):** Ratio of tokens and latency consumed by orchestrator vs. raw task execution.
8. **Recovery Efficiency (RE):** Percentage of verification-failed missions successfully transitioning to `VERIFIED` via `RECOVERING`.
9. **Unauthorized Action Rate (UAR):** Number of tool calls dispatched without valid delegation scope.

---

## 8. Statistical Analysis Plan

1. **Paired Comparisons:** Because the same tasks and model families are evaluated across conditions, binary outcomes (VSR, FCR) are evaluated using the **two-tailed McNemar test** for paired nominal data.
2. **Continuous Distributions:** Cost (USD) and latency (ms) distributions violate normality assumptions (log-normal / heavy-tailed); evaluated using the **Wilcoxon signed-rank test**.
3. **Confidence Intervals:** All rates reported with **95% Wilson score intervals**.
4. **Effect Sizes:** Reported as Cohen's $h$ for proportions and Cohen's $d$ / Cliff's delta for continuous metrics.
5. **Multiple Comparison Correction:** $p$-values adjusted using the **Benjamini-Hochberg False Discovery Rate (FDR)** procedure ($\alpha = 0.05$).

---

## 9. Stopping Rules & Exclusion Criteria

- **Stopping Rules:** A run terminates if (1) verified completion achieved, (2) maximum turns reached ($T_{\max} = 5$), (3) mission budget exhausted, (4) irreversible error encountered, or (5) human operator cancellation.
- **Exclusion Rules:** Runs are excluded only in the event of local infrastructure power failure or unhandled OS abort. Rate-limit errors, network drops, and model formatting failures are **retained** in data as operational failures.
- **Hypothesis Modifications:** Any post-hoc analysis differing from this document must be explicitly designated as *Exploratory / Post-Hoc Analysis*.
