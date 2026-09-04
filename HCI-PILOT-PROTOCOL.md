# HCI Pilot Study Protocol: Human-in-the-Loop Mission Control vs. Chat Interaction
**Research Program:** Jonas Abde Intelligence Systems Research Program — Q3 2026  
**Document ID:** `HCI-PILOT-PROTOCOL-v0.3`  
**Classification:** Human Factors & Operator Interaction Pilot Protocol  
**Principal Investigator:** Jonas Abde  
**Sample Target:** $N = 12$ Professional Software / SRE Engineers (Range: 8–16)  
**Precedes:** Main Formal Study ($N = 152$, preregistered in `STUDY-006`)  
**Status:** **ACTIVE PILOT PROTOCOL**  

---

## 1. Purpose & Scope of Pilot

Prior cognitive modeling in `STUDY-006` simulated 64 synthetic personas using GOMS keystroke-level modeling ($N=0$ live human participants). To transition from simulation to live human-subjects research without wasting recruitment resources on uncalibrated experimental software, this **Pilot Study** evaluates a focused sample of $N=12$ domain practitioners.

### Specific Pilot Objectives:
1. **Task Calibration:** Verify that SWE, SRE, and Data tasks can be completed within the 45-minute participant window without ceiling or floor effects.
2. **Instrumentation Validation:** Verify that telemetry hooks capture keystrokes, pause/resume events, and attention switches with $<10\text{ ms}$ jitter.
3. **Variance Estimation:** Measure empirical standard deviations of Human Turns per Verified Outcome (HEVO) and NASA-TLX scores to compute the final, high-precision power analysis for the main study.
4. **UX Friction & Confusion Detection:** Identify interface ambiguities in the Mission Control exception card UI vs. streaming chat consoles.
5. **Screening Protocol Validation:** Validate inclusion criteria (professional Git, CLI, and debugging experience).

---

## 2. Participant Recruitment & Inclusion Criteria

### Sample Size
- Target: **$N = 12$ participants** (balanced across 4 experimental arms: 3 per arm).
- Minimum Acceptable: $N = 8$; Maximum Ceiling: $N = 16$.

### Inclusion Criteria:
- Minimum 2 years professional experience in software engineering, DevOps, SRE, or data platform engineering.
- Active daily use of AI coding assistants or agent tools (e.g., GitHub Copilot, Cursor, Claude Code).
- Fluency in reading and debugging Python and standard shell scripts.

### Exclusion Criteria:
- Prior involvement in the Jonas Abde Intelligence Systems Research Program.
- Familiarity with SPEC-001 or in-house agent codebase.

---

## 3. Study Design & Experimental Arms

A between-subjects $2 \times 2$ factorial pilot design:

| Arm ID | Interface Modality | Verification & Governance | Description |
| :--- | :--- | :--- | :--- |
| **Arm 1 (Chat-Baseline)** | Linear Chat Console | Self-Reported (Unconstrained) | Streaming markdown terminal; user reviews raw text |
| **Arm 2 (Chat-Gated)** | Linear Chat Console | Deterministic Evidence Gate | Chat terminal with test runner feedback |
| **Arm 3 (Mission-Ungated)**| Mission Dashboard | Self-Reported (Unconstrained) | Structured mission cards without evidence requirement |
| **Arm 4 (Full Mission UX)**| Mission Dashboard | SPEC-001 Logical Assurance | Exception-based progressive cards + deterministic receipts |

---

## 4. Workload Protocol & Tasks

Each participant executes **4 standardized operational tasks** (25 minutes total task time):
1. `TASK-P1 (SWE)`: Debug pagination slice boundary with a regression test fixture.
2. `TASK-P2 (SRE)`: Diagnose pod crashloop and review rollback receipt.
3. `TASK-P3 (FAULT)`: Simulated agent hallucination attempting out-of-scope directory deletion.
4. `TASK-P4 (BUDGET)`: Long-running query reaching token ceiling requiring manual budget override.

---

## 5. Metrics & Instrumentation

### Primary Measures:
- **HEVO (Human Turns per Verified Outcome):** Exact count of human input prompts/clicks required to achieve a verified result.
- **Cognitive Workload (NASA-TLX):** 6-subscale subjective workload assessment administered post-task.
- **Undetected Error Rate (UER):** Frequency with which participant accepts an erroneous or unverified agent output.
- **Time on Task (TOT):** Wall-clock duration in seconds.

### Telemetry Pipeline:
- All interactions logged to append-only JSON session files via `telemetry/events.py`.
- No personally identifiable information (PII) recorded; participants assigned random anonymized tokens (`P-01` through `P-12`).

---

## 6. Power Recalculation Trigger

Upon completion of $N=12$ pilot trials:
1. Compute pooled variance $s^2$ across the 4 arms for HEVO and NASA-TLX.
2. Re-run G*Power calculation with $\alpha = 0.05$ and power $1 - \beta = 0.90$.
3. Freeze the final participant target $N_{\text{main}}$ in `STUDY-006-AMENDMENT-01.md`.
4. **Mandatory Rule:** Hypotheses must not be altered post-hoc based on pilot trends.
