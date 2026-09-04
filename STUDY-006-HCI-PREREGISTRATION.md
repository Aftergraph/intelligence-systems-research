# STUDY-006: Preregistration Protocol — Human-Intelligence Interaction (HCI) Trial
**Program:** Jonas Abde Intelligence Systems Research Program — Q3 2026  
**Document ID:** `STUDY-006-PREREG-001`  
**Date:** 4 September 2026  
**Status:** PREREGISTERED STUDY PROTOCOL — EMPIRICAL RECRUITMENT PENDING  
**Preregistration Repository:** OSF / AsPredicted Format  
**Authors:** Jonas Abde Research Program  
**Investigated Claim:** `C-004 (H-003)`  

---

## 1. Scientific Objective & Integrity Disclaimer
> [!IMPORTANT]
> **Scientific Integrity Notice:** The Jonas Abde Research Program **does not claim** that human users empirically prefer mission-centric UX over chat-only interfaces today. Current claims are based exclusively on architectural prototype workflows and cognitive walkthroughs. This study protocol is preregistered to collect rigorous, reproducible empirical human participant data under controlled laboratory conditions.

---

## 2. Experimental Design

### 2.1 Design Topology
- **Study Type:** Between-subjects randomized controlled trial ($4 \times 1$).
- **Modalities Evaluated:**
  - Arm 1: **Chat-Only Baseline** (Natural language conversational turn-taking, verbose streaming output).
  - Arm 2: **Traditional GUI** (Forms, tables, button-triggered execution).
  - Arm 3: **Hybrid Agent UI** (Chat interface with embedded interactive widgets and tool approval popups).
  - Arm 4: **Mission-Centric UX (SPEC-001)** (Declarative contract preview, exception-first "Needs You" alerting, progressive disclosure).
- **Sample Size ($N$):** Determined via `experiments/hci_study_package/power_analysis.py`:
  - Pilot variance calibrated effect size $d = 0.65$, $\alpha = 0.05$, power $(1-\beta) = 0.80$.
  - Required sample size: $n = 38$ per arm, resulting in **$N = 152$ total participants** across 4 arms (or $N=76$ if restricted to a 2-arm Chat vs. Mission comparison).

### 2.2 Standardized Tasks (4 Multi-Step Workloads)
Each participant completes 4 sequential enterprise workflows:
1. **Task 1 (Production Hotfix Deployment):** Patch an authentication vulnerability, run unit tests, and deploy to staging.
2. **Task 2 (Database Schema Migration & Rollback):** Execute an asynchronous schema change with strict zero-downtime budget constraints.
3. **Task 3 (Adversarial Prompt Injection Exposure):** The agent encounters an indirect prompt injection payload within external repository issue comments attempting to delete backup tables.
4. **Task 4 (Budget Exhaustion & Multi-Service Recovery):** Cloud API costs surge during batch data processing, testing operator interruption and graceful suspension.

---

## 3. Dependent Variables & Measurement Instruments

1. **Human Effort per Verified Outcome (HEVO):**
   - Total number of active user interventions, clarifications, prompts, and tool approvals per completed task.
2. **Cognitive Workload (NASA-TLX):**
   - Standardized 6-subscale NASA Task Load Index (Mental, Physical, Temporal, Performance, Effort, Frustration) administered immediately post-task.
3. **Undetected Error / Hallucination Rate (UEHR):**
   - Percentage of agent hallucination errors, unverified state transitions, or malicious actions that the human operator failed to catch before signing off.
4. **Calibrated Reliance & Trust (Explicitly NOT Maximizing Trust):**
   - Measures Appropriate Reliance = (Complied when Valid + Intervened when Flawed) / Total Checkpoints.
   - Specifically measures Overtrust (approving flawed actions) and Undertrust (unnecessary manual checks).
5. **Time to Verified Outcome (TVO):**
   - Wall-clock seconds from initial instruction to ground-truth verified completion.
6. **Usability (SUS / UMUX-Lite):**
   - Standardized 10-item System Usability Scale.

---

## 4. Formal Statistical Hypotheses & Power Calculation

- **Hypothesis $H_{1}$ (Effort Reduction):** $HEVO_{\text{Mission}} < 0.60 \times HEVO_{\text{Chat}}$ ($d \ge 0.65$).
- **Hypothesis $H_{2}$ (Cognitive Load Reduction):** $TLX_{\text{Mission}} \le 0.75 \times TLX_{\text{Chat}}$ ($d \ge 0.65$).
- **Hypothesis $H_{3}$ (Error Catch Rate):** $UEHR_{\text{Mission}} \le 0.30 \times UEHR_{\text{Chat}}$ ($p < 0.001$, Fisher's exact test).
- **Hypothesis $H_{4}$ (Reliance Calibration):** Mission UI significantly reduces overtrust errors without increasing undertrust latency ($p < 0.01$).

### Power Calculation:
Executing `python experiments/hci_study_package/power_analysis.py` establishes that achieving 80% power at $\alpha=0.05$ across 4 arms with anticipated effect size $d = 0.65$ requires $n=38$ participants per arm, for a **total target recruitment of $N=152$**.


---

## 5. Current Claim Classification
Pending execution and peer review of this 64-participant study, claim `C-004` is formally classified in the research registry as:
`PARTIALLY_SUPPORTED (PROTOTYPE DESIGN ONLY — AWAITING HUMAN HCI TRIAL)`
