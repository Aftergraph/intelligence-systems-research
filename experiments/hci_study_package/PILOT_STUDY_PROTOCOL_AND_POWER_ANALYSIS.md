# Pilot Study Protocol, Statistical Power Analysis & Reliance Rubric
**Study ID:** `STUDY-006-PILOT-AND-POWER`  
**Program:** Jonas Abde Intelligence Systems Research Program — Q3 2026  
**Status:** Preregistration Ready (Pending IRB Approval & Participant Recruitment)  

---

## 1. Sequence of Execution

To eliminate arbitrary sample sizing and ensure methodological rigor:
```
[Phase 1: Pilot Study (N=16)]
       │
       ▼
[Estimate Variance & Effect Size (sigma_HEVO, sigma_TLX)]
       │
       ▼
[Finalize Tasks & Instrumentation (Screen recordings, Eye tracking / KLM)]
       │
       ▼
[Formal Statistical Power Analysis (G*Power standard)]
       │
       ▼
[Formal OSF / AsPredicted Preregistration]
       │
       ▼
[Phase 2: Main Study Execution (N=152)]
```

---

## 2. Four Experimental Modalities

The main trial evaluates four between-subjects interaction conditions:
1. **Modality 1 (Chat-Only Agent):** Standard streaming text chat (e.g., Cursor / Copilot Chat style). Operator observes verbose step logs and interacts via natural language prompts.
2. **Modality 2 (Traditional GUI):** Web dashboard with traditional form inputs, status tables, and button-triggered REST actions.
3. **Modality 3 (Hybrid Agent UI):** Chat interface with embedded interactive widgets and raw tool-call approval dialogs.
4. **Modality 4 (Mission-Centric Interface - SPEC-001):** Goal-first declarative view displaying objective, active budget burn, and "Needs You" exception cards. Execution logs are held out-of-band; operator only acts on structured policy/verification exceptions.

---

## 3. Power Analysis & Sample Size Determination

Using `experiments/hci_study_package/power_analysis.py` (two-tailed $\alpha = 0.05$, $1 - \beta = 0.80$):

| Scenario | Anticipated Effect Size (Cohen's $d$) | Sample Size per Arm ($n$) | Total Sample Size ($N$, 4 Arms) |
| :--- | :--- | :--- | :--- |
| **Conservative (Medium Effect)** | $d = 0.50$ | $n = 63$ | $N = 252$ |
| **Calibrated from Pilot Simulation** | $d = 0.65$ | $n = 38$ | **$N = 152$ (Design Target)** |
| **Optimistic (Large Effect)** | $d = 0.80$ | $n = 25$ | $N = 100$ |

*Correction:* The initial preliminary placeholder of $N=64$ is superseded by the power-calculated target of **$N=152$ ($n=38$ per arm)** for the full 4-arm design, or $N=76$ if restricted to a 2-arm binary comparison (Chat vs. Mission).

---

## 4. Measurement Instruments & Calibration of Trust

### Mandatory Primary Metrics:
- **Verified Success Rate (VSR):** Percentage of trials where outcome matches ground truth.
- **Time to Verified Outcome (TVO):** Wall-clock seconds from task assignment to verified state.
- **Human Effort per Verified Outcome (HEVO):** Count of manual operator turns/interventions.
- **Takeover Latency:** Reaction time (seconds) between an exception event and operator input.
- **Approval Errors:** Approvals granted to invalid or malicious actions (false positives).
- **Cognitive Workload:** NASA-TLX 6-subscale score (Mental, Physical, Temporal, Performance, Effort, Frustration) normalized 0–100.
- **Usability:** System Usability Scale (SUS) or UMUX-Lite score.

### Reliance and Trust Calibration (Explicitly NOT Maximizing Trust):
High trust is dangerous if the agent is hallucinating. We measure **Appropriate Reliance**:
$$\text{Reliance Calibration Score} = \frac{\text{Complied when Valid} + \text{Intervened when Flawed}}{\text{Total Verification Checkpoints}}$$
- **Overtrust (Automation Bias):** Approving an unverified or corrupted action because "the agent said it worked".
- **Undertrust (Excessive Verification Overhead):** Manually checking benign steps despite valid Tier 2 cryptographic receipts.
- **Goal:** Minimize both Overtrust and Undertrust, maximizing **Calibrated Reliance**.
