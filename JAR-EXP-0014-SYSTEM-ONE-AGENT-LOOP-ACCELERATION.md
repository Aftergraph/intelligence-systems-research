# JAR-EXP-0014 — System One Agent-Loop Acceleration

**State:** PREREGISTRATION DRAFT — NO EMPIRICAL CLAIMS YET  
**Program:** Aftergraph Intelligence Systems Research  
**Date:** 2026-09-19  
**Scope:** Fast structured decision substitution inside agent loops  
**Primary treatment:** TypeSafe AI Jev (System One)  
**Control:** Generative LLM classification/decision calls  
**Architecture boundary:** Advisory decision layer only; no new authority, execution, truth, or verification plane.  
**Stack dependency:** Draft PR #112 is intentionally stacked on Protocol v0.2 draft PR #111 so the historical STUDY-012 scope fix is inherited rather than duplicated.

> [!IMPORTANT]
> This experiment is prospective. TypeSafe/third-party speed and cost figures are treated as external claims to test, not as Aftergraph evidence. No result from STUDY-012 is modified, pooled, or reinterpreted by this experiment.

## 1. Research question

Can a fast typed decision model replace selected generative-LLM decision calls inside an agent loop while preserving mission correctness, safety, and verification quality, and materially reducing decision latency, cost, and end-to-end wall-clock time?

Canonical loop under test:

```
state
  -> decision
  -> tool/action candidate
  -> authority admission
  -> execution
  -> evidence
  -> evaluation
  -> continue / stop / escalate
```

The treatment changes only the **decision** implementation for eligible low-entropy judgments.

## 2. Architectural non-overlap

Jev/System One is not granted execution authority.

- **AIE / Trust Gateway:** remain authoritative for identity, delegation, capability admission, policy and execution-time revalidation.
- **WORKS:** remains authoritative for durable execution/recovery.
- **Sentinel / deterministic verifiers:** remain authoritative for verification/evidence classification.
- **LLM:** remains responsible for open-ended planning, synthesis, generation, debugging and novel reasoning.
- **System One/Jev:** may classify state into typed decisions/probabilities used for routing, prioritization, continuation, escalation and pre-tool risk screening.

A Jev answer is therefore an **advisory decision receipt**, never a VERIFIED outcome.

## 3. Eligible decision classes

The treatment is limited to decisions expressible as typed classifications:

1. `route_model` — Choice: cheapest adequate model class.
2. `route_tool_family` — Choice: relevant tool family.
3. `continue_loop` — Noul: whether more work is required.
4. `result_sufficient` — Noul: whether current evidence satisfies the local decision criterion.
5. `needs_human` — Noul: whether owner/human intervention is required.
6. `risk_level` — Score/Choice: pre-tool risk classification.
7. `retryable_failure` — Noul: whether a tool/provider failure is retryable.
8. `evidence_conflict` — Noul: whether observations conflict and require escalation.

Open-ended planning, code generation, root-cause reasoning and final user-facing synthesis are explicitly ineligible.

## 4. Arms

| Arm | Description |
|---|---|
| **A — LLM-only control** | Existing agent loop; eligible decisions are made by a generative LLM with structured output. |
| **B — Jev direct** | Eligible decisions are made by Jev; no LLM fallback except on transport/schema failure. |
| **C — Jev cascade** | Jev decides when calibrated confidence is above the frozen threshold; otherwise fallback to the same LLM used by Arm A. |

All non-decision components, tools, prompts, task ordering and authority checks remain identical across arms.

## 5. Primary hypotheses and frozen success bars

### H1 — Decision latency
For eligible decisions, Arm C median decision latency is at least **5x lower** than Arm A.

### H2 — Decision cost
Arm C decision-layer monetary cost per eligible decision is at least **70% lower** than Arm A.

### H3 — End-to-end agent wall-clock
On decision-heavy missions, Arm C median mission wall-clock is at least **20% lower** than Arm A.

### H4 — Mission non-inferiority
Arm C mission success rate is non-inferior to Arm A with a frozen margin of **2 percentage points**.

### H5 — Safety
For preregistered critical-risk cases, unauthorized-action rate remains **0** in all arms. Any unauthorized admitted action is an automatic treatment failure.

### H6 — Calibration
For binary Noul decisions, Jev probability quality is evaluated with Brier score and reliability bins. No calibration-improvement claim is made unless Jev is better than the control and confidence intervals exclude zero difference.

The vendor-reported acceleration range is not used as a success bar.

## 6. Workload

Minimum confirmatory set:

- **3 task families:** repository lookup/extraction, bounded implementation/debugging, operational triage.
- **30 missions per family per arm** = 270 mission runs minimum.
- Each mission must contain at least 3 preregistered eligible decision points.
- Critical-risk adversarial pack: at least 30 tool-call candidates covering destructive shell, credential exposure, authority mismatch, stale state, replay and ambiguous approval.

Tasks are frozen before execution and randomized across arms.

## 7. Measurements

Per decision:

- decision type;
- model/provider/version;
- input bytes/tokens when available;
- latency ms;
- cost USD;
- selected answer;
- probability distribution/confidence;
- fallback reason;
- reference label;
- correctness;
- authority result;
- receipt hash.

Per mission:

- wall-clock seconds;
- total model calls;
- generative LLM calls avoided;
- Jev calls;
- fallback count;
- tool calls;
- retries;
- human interventions;
- task success;
- verified outcome;
- unauthorized action count;
- false-stop / false-continue count;
- total cost.

## 8. Confidence-gated cascade

The cascade threshold is frozen before the confirmatory run.

Initial calibration phase may estimate a threshold, but its data is excluded from confirmatory analysis.

Rules:

1. schema/transport failure -> fallback;
2. confidence below frozen threshold -> fallback;
3. any authority-sensitive ambiguity -> fallback;
4. Jev cannot override a denial from AIE/TG;
5. Jev cannot mark a mission VERIFIED;
6. contradictory evidence -> escalate to verifier/LLM, never silently resolve.

## 9. Decision receipt

Every System One decision produces a durable receipt conforming to:

`aftergraph.system-one-decision/0.1`

The receipt records state hash, question contract, answer probabilities, confidence, routing/fallback outcome, model identity and provenance. Raw secrets and full private state are prohibited from the receipt.

## 10. Analysis

Primary paired comparisons:

- latency ratio and median delta;
- decision cost ratio;
- mission wall-clock delta;
- mission success-rate difference;
- unauthorized-action count;
- false-stop/false-continue rates;
- LLM-call reduction;
- fallback rate.

Use bootstrap confidence intervals for continuous timing/cost metrics and Wilson/Newcombe intervals for binary success rates where applicable.

Report micro-level decision acceleration separately from end-to-end mission acceleration.

## 11. Falsification conditions

The treatment is not promoted if any of the following occurs:

- unauthorized-action rate > 0 in critical-risk cases;
- mission success violates the 2pp non-inferiority margin;
- end-to-end wall-clock improvement < 20%;
- decision-cost reduction < 70%;
- confidence-gated fallback rate is so high that Arm C does not materially reduce generative LLM calls;
- probability outputs are materially miscalibrated around the chosen confidence threshold;
- a hidden coupling causes Jev decisions to bypass canonical authority or verification.

A fast classifier that degrades correctness is a failed treatment.

## 12. External inputs and evidence discipline

Current design is informed by:

- TypeSafe AI System One/Jev documentation: typed state + Noul/Choice/Score decisions with probabilities.
- TypeSafe cookbook examples showing low-latency structured decisions and parallel question batching.
- LangChain middleware patterns for model routing and pre-tool interception.

These are **design inputs only**. Their reported benchmark results are not local evidence.

## 13. Promotion target

If the experiment passes, the production pattern is:

```
Agent state
   |
   +--> System One decision accelerator
   |       |-- high confidence --> typed route
   |       '-- low confidence --> LLM fallback
   |
   +--> AIE / Trust Gateway admission
   +--> WORKS execution
   +--> Evidence
   '--> Sentinel / deterministic verification
```

Promotion means enabling the accelerator behind a feature flag for eligible decision classes. It does not create a new Aftergraph plane.

## 14. Current gate

**PREREGISTRATION_DRAFT**

Before live execution:

- freeze workload;
- freeze question contracts;
- freeze cascade threshold;
- pin TypeSafe model version returned by the API;
- pin control model(s);
- implement receipt schema + deterministic validator;
- implement adapters;
- run zero-network conformance;
- perform bounded calibration;
- issue explicit execution approval.

No confirmatory network run is authorized by this document.
