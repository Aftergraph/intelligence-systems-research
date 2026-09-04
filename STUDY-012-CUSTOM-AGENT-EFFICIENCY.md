# STUDY-012: Custom Research Agent vs Default Session Prompt — Efficiency and Output-Discipline Comparison
**Program:** Jonas Abde Intelligence Systems Research Program — Q3 2026
**Document ID:** `STUDY-012-AGENT-EFF`
**Date:** 4 September 2026
**Status:** EXPLORATORY PILOT REPORT — NOT PREREGISTERED, NOT CONFIRMATORY
**Classification:** Level E0–E1 internal pilot (researcher intuition + secondary observation)
**Author:** Jonas Abde Research Program

> [!CAUTION]
> This is a small-sample exploratory pilot ($N=3$ per arm). It is not preregistered, not powered, and not confirmatory. No maturity claim, conformance claim, or standardization claim may be advanced from this report. All findings are hypotheses for a future preregistered study.

---

## 1. Research Question

Does the workspace custom agent (`.github/agents/intelligence-systems-research.agent.md`) produce more output-disciplined, evidence-separated research answers than the default session prompt, and at what token cost?

## 2. Hypotheses (Post-Hoc — Exploratory Only)

- **H1 (Output discipline):** The custom agent emits the repository output contract (question, evidence, hypothesis, method, findings/limitations, artifacts) more consistently than the default prompt.
- **H2 (Cost):** The custom agent adds a fixed context overhead of approximately 1,500 tokens per invocation.
- **H0 (Null):** No systematic difference in structure, correctness, or cost exists between arms.

No success threshold was frozen. Falsification condition for a future confirmatory study: structure-compliance difference $< 20$ percentage points or overhead $> 3{,}000$ tokens per invocation.

## 3. Method

### 3.1 Arms

| Arm | Description |
|---|---|
| **A (Custom)** | `Intelligence Systems Researcher` subagent, governed by `.github/agents/intelligence-systems-research.agent.md` |
| **B (Baseline)** | Default `Explore` subagent, no custom system prompt |

### 3.2 Task (Identical)

> What is the program's core hypothesis, and what is the cheapest repository-local check for a new claim? Constraints: read-only, no edits, no expensive commands. Cite repository paths by name. Keep answer under 200 words.

### 3.3 Trials

$N=3$ per arm ($N=6$ total), executed 2026-09-04. One earlier N=1 smoke test preceded this pilot and is excluded from tallies.

### 3.4 Metrics

- **Structure compliance:** presence of 6 output-contract sections (question/scope, evidence, hypothesis/decision, method, findings/limitations, artifacts).
- **Word count:** whitespace-delimited tokens in the returned answer.
- **Read-only compliance:** no file edits, no expensive commands (`pytest -v`, full conformance, live runs).
- **Context overhead:** file size of the custom agent definition (chars/4 token estimate).
- **Correctness:** factual agreement with `MASTER_RESEARCH_PROGRAM.md` §2 and `02-RESEARCH-PROTOCOL-v0.1.md` claim-registry rule.

### 3.5 Environment

- Workspace: `Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026`
- Verification baselines (same day): `pytest -q` → 64 passed; `conformance/runner.py` → 14/14 passed.
- No live API calls were made for this study. Subagent invocations are the measured instrument, not benchmark workloads.

## 4. Results

### 4.1 Structure Compliance

| Trial | Arm | Sections Present / 6 | Sections |
|---|---|---|---|
| A1 | Custom | 6/6 | question, evidence, hypothesis, method, findings, artifacts |
| A2 | Custom | 6/6 | question, evidence, hypothesis, method, findings, artifacts |
| A3 | Custom | 6/6 | question, evidence, hypothesis, method, findings, artifacts |
| B1 | Baseline | 2/6 | hypothesis + method (implicit) |
| B2 | Baseline | 3/6 | hypothesis, method, partial findings |
| B3 | Baseline | 3/6 | hypothesis, method, partial findings |

**Compliance rate:** Custom 18/18 (100%), Baseline 8/18 (44.4%). Difference: **+55.6 percentage points**.

### 4.2 Verbosity

| Trial | Arm | Words |
|---|---|---|
| A1 | Custom | ~170 |
| A2 | Custom | ~150 |
| A3 | Custom | ~140 |
| B1 | Baseline | ~110 |
| B2 | Baseline | ~130 |
| B3 | Baseline | ~120 |

**Mean:** Custom ~153 words, Baseline ~120 words. Custom answers are ~28% longer, driven by section headers and limitation statements.

### 4.3 Read-Only Compliance

Both arms: 6/6 trials read-only, no edits, no expensive commands. No difference.

### 4.4 Correctness

Both arms correctly stated the core hypothesis (intent → mission → … → verified outcome → recovery, falsifiable) and the cheapest check (claim-registry lookup before any test execution). Baseline trials cited more specific repository paths per answer (mean ~6 vs ~4); custom trials cited the audit registry and protocol rule more consistently.

### 4.5 Context Overhead (Measured)

| Artifact | Bytes | Est. Tokens (chars/4) |
|---|---|---|
| `.github/agents/intelligence-systems-research.agent.md` | 5,995 | ~1,499 |
| `schemas/mission.v0alpha1.json` | 3,856 | — |
| `schemas/intelligence-system.v0alpha1.json` | 2,285 | — |
| `schemas/evidence.v0alpha1.json` | 2,081 | — |
| `schemas/delegation.v0alpha1.json` | 1,930 | — |

The custom agent adds a **fixed ~1,500-token overhead per invocation**. No variable cost was measured.

## 5. Economic Perspective

Cost model per invocation:

$$\text{Total} = C_{\text{fixed}} + C_{\text{answer}} + C_{\text{retries avoided}}$$

- $C_{\text{fixed}}$ (custom only): ~1,500 tokens.
- $C_{\text{answer}}$: custom ~153 words vs baseline ~120 words (~+33 words ≈ +44 tokens at 0.75 words/token).
- $C_{\text{retries avoided}}$: unmeasured in this pilot ($N=6$, single-turn task, no retries observed in either arm).

**Finding:** In this pilot the custom agent strictly costs more (~1,544 extra tokens per call) with no measured saving. Net benefit requires downstream effects not observed here: fewer clarification turns, fewer verification re-runs, or fewer false-completion incidents. This mirrors the program's own Economic Inversion logic (STUDY-003: control-plane tax amortized by rescued work) but that result does **not** transfer to this pilot — it was measured on 800 benchmark workloads, not on prompt comparison.

**Break-even condition (hypothesis):** if the custom agent prevents one ~1,500-token clarification round per invocation, it pays for itself. This was not tested.

## 6. Limitations and Confounders

1. **Small sample:** $N=3$ per arm. No confidence intervals or significance tests are reported; any test would be underpowered.
2. **Not preregistered:** hypotheses are post-hoc. Confirmation bias risk is uncontrolled.
3. **Single task:** one short read-only question. No generalization to implementation, debugging, or multi-turn work.
4. **Rater bias:** the same researcher scored structure compliance using the custom agent's own output contract — circularity favors Arm A.
5. **Instrument confound:** arms differ by subagent type (`Intelligence Systems Researcher` vs `Explore`), not only by system prompt.
6. **No blinding:** trials were not randomized or blinded.
7. **No cost measurement:** token counts are file-size estimates, not metered usage. No latency, money, or energy measured.
8. **No downstream outcomes:** retries, false completions, and human effort — the quantities that would justify overhead — were not measured.

## 7. Objections (Research Opponent)

- **OBJ-012-1:** Structure compliance is a cosmetic metric; baseline answers contained equivalent facts with fewer words. *Response:* accepted as partial — factual parity held in this pilot; structure value is in auditability, not information content.
- **OBJ-012-2:** The ~1,500-token overhead is pure tax with no demonstrated return. *Response:* accepted for single-turn tasks; return hypothesis (fewer retries) is untested.
- **OBJ-012-3:** Baseline gave more specific file pointers, suggesting the custom prompt constrains retrieval breadth. *Response:* plausible; needs a retrieval-recall metric in a future study.

## 8. Conclusion

Exploratory pilot only: the custom agent enforces output structure (100% vs 44.4% section compliance) at a fixed cost of ~1,500 tokens per invocation plus ~28% longer answers. No economic benefit was demonstrated. The decision to use the custom agent is currently a **governance preference** (auditability, falsification discipline), not an evidence-backed efficiency claim.

## 9. Recommended Next Study (Preregistered)

To convert this into evidence, preregister a confirmatory study with:

- $N \ge 30$ tasks per arm across 3 task families (read-only Q&A, implementation, debugging).
- Blinded raters, randomized order, independent scoring rubric (structure, factual accuracy, retrieval recall, action safety).
- Metered tokens, latency, turns-to-completion, retry count, and human interventions.
- Pre-frozen SEOI (e.g. structure compliance $\Delta \ge 20$pp, turns-to-completion reduction $\ge 15\%$) and falsification conditions.
- Power analysis per `scripts/study011_power_analysis.py` conventions.

## 10. Provenance

- Custom agent: `.github/agents/intelligence-systems-research.agent.md` (5,995 bytes, 83 lines).
- Protocol reference: `02-RESEARCH-PROTOCOL-v0.1.md` (evidence tiers E0–E6, claim states, hypothesis rule).
- Claim registry: `data/claim_registry.csv` (C-001…C-018); hypothesis registry: `data/hypothesis_registry.csv` (H-001…H-007).
- Verification baselines: `pytest -q` 64 passed; `conformance/runner.py` 14/14 passed (2026-09-04).
- Prior pilot: N=1 smoke test (excluded from tallies).

---
*End of STUDY-012 Exploratory Pilot Report. No new claims are registered from this report. No registries were modified.*
