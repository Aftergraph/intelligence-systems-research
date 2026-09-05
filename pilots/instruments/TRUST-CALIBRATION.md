# TRUST-CALIBRATION — STUDY-006 Instrument

**Protocol ID:** `STUDY-006-PREREG-001`  
**Measure:** Calibrated Reliance & Trust (explicitly NOT maximizing trust)  
**Administration:** Pre-task (baseline) and post-task (per arm comparison)  
**Type:** Self-report + Behavioral Proxies

---

## 1. Overview

STUDY-006 measures **appropriate reliance** rather than raw trust scores. The instrument captures:

1. **Explicit self-report** of trust/confidence in the agent
2. **Behavioral proxies** of overtrust vs. undertrust

**Goal:** Measure whether the Mission-Centric UI reduces overtrust (approving flawed actions) without increasing undertrust (unnecessary manual checks).

---

## 2. Self-Report Scale (Pre/Post Task)

**Instructions:** For each checkpoint, rate your confidence in the agent's proposed action.

| Item | Statement | Scale |
|------|-----------|-------|
| TR1 | I believe the agent's action is correct. | 1–5 (Strongly Disagree → Strongly Agree) |
| TR2 | I feel confident allowing the agent to proceed. | 1–5 |
| TR3 | I would intervene if I were uncertain. | 1–5 |
| TR4 | The agent is competent in this domain. | 1–5 |
| TR5 | I would recommend this agent to a colleague. | 1–5 |

**Administration:**
- **Pre-task:** TR1, TR2, TR4 (baseline)
- **Post-task:** All items (per task checkpoint)

---

## 3. Behavioral Proxies (Platform-Recorded)

| Proxy | Definition | Measurement |
|-------|------------|-------------|
| **Intervention Count** | Total number of active user interventions, clarifications, prompts, and tool approvals per task | Count |
| **Takeover Latency** | Time (seconds) from agent alert to user intervention (when user intervenes) | Timestamp delta |
| **Approval Rate** | Percentage of agent actions approved without review | (Approvals / Total Actions) × 100 |
| **Intervention Timing** | When interventions occur (early vs. late in task) | Task phase |

---

## 4. Calibration Metric (Primary Outcome)

**Appropriate Reliance Score:**
```
Reliance = (Complied When Valid + Intervened When Flawed) / Total Checkpoints
```

| Error Type | Definition |
|------------|------------|
| **Overtrust** | Agent action was flawed but user approved without intervention |
| **Undertrust** | Agent action was valid but user unnecessarily intervened |

**Hypothesis (H4):** Mission UI significantly reduces overtrust errors without increasing undertrust latency.

---

## 5. Analysis Plan

1. Compare mean TR1–TR5 scores across 4 arms (ANOVA)
2. Compare behavioral proxies (intervention count, takeover latency) across arms
3. Calculate Reliance Score per participant; compare means across arms
4. Test H4 using Fisher's exact test on overtrust/undertrust error counts

---

## 6. Notes

- Self-report items adapted from standardized trust scales (Goddard et al., 2020)
- Behavioral proxies logged automatically by platform (see SESSION-LOGGING.md)
- All items randomized to minimize order effects

---

*Instrument version: 1.0 — Matches STUDY-006 preregistration (Section 3.4)*
