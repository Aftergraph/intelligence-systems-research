# SESSION SCRIPT — STUDY-006 HCI Trial

| Field | Value |
|-------|-------|
| **Study ID** | STUDY-006-PREREG-001 |
| **Target Duration** | 60–90 minutes |
| **Script Type** | Standardized by Arm |

---

## PRE-SESSION CHECKLIST

1. Verify participant consent form signed
2. Confirm participant eligibility (AI tool usage weekly, language fluency)
3. Set arm assignment (randomized 1:1:1:1 across 4 arms)
4. Prepare recording equipment (if consented)
5. Load task environment for assigned arm
6. Check NASA-TLX and SUS survey links ready

---

## OPENING SCRIPT (All Arms)

**Moderator**:

> Welcome. Thank you for participating in this study.
>
> In this session, you will complete four realistic work tasks using an AI assistant. The tasks involve deploying code, managing databases, handling security alerts, and recovering from budget overruns.
>
> We are testing how different interface designs affect your workflow. There is no "correct" way to do this—just complete each task as you normally would.
>
> The session takes 60–90 minutes. You may stop at any time. If you're comfortable, please begin with Task 1.

**Start Recording** (if consented)

---

## ARM-SPECIFIC INSTRUCTIONS

### Arm 1: Chat-Only Baseline

> This interface is a chat window. Type your commands and questions in natural language. The assistant will respond in text. You may ask follow-up questions as needed.
>
> Note: You must explicitly type commands to execute actions (e.g., "deploy to staging"). The assistant will not execute anything without your text command.

### Arm 2: Traditional GUI

> This interface uses forms, tables, and buttons. To execute actions, fill out the form fields and click the appropriate buttons.
>
> Note: Use the "Execute" button to confirm actions. Do not proceed unless you've reviewed the form details.

### Arm 3: Hybrid Agent UI

> This interface combines chat with interactive widgets. You may type commands or use the embedded tools and approval popups.
>
> Note: Actions requiring approval will show a popup—click "Approve" or "Reject" as needed. You may also type questions in the chat.

### Arm 4: Mission-Centric UX (SPEC-001)

> This interface shows mission objectives and exceptions first. Alerts appear when human attention is needed ("Needs You"). Use progressive disclosure to reveal details.
>
> Note: The assistant will propose actions; you may accept, reject, or modify. Focus on reviewing exceptions before allowing execution.

---

## TASK INTRODUCTIONS (All Arms)

**Task 1 (Production Hotfix Deployment)**:

> Your task: Patch an authentication vulnerability, run unit tests, and deploy to staging.
>
> Begin when ready. Use this interface to complete the task.

**Task 2 (Database Schema Migration & Rollback)**:

> Your task: Execute an asynchronous schema change with a zero-downtime budget.
>
> Begin when ready.

**Task 3 (Adversarial Prompt Injection Exposure)**:

> Your task: An agent has encountered a suspicious repository comment. Review the issue and respond appropriately.
>
> Begin when ready.

**Task 4 (Budget Exhaustion & Recovery)**:

> Your task: Cloud costs have surged during batch processing. Interrupt or suspend the batch gracefully.
>
> Begin when ready.

---

## POST-TASK SURVEY (All Arms)

After each task:

**Moderator**:

> Please complete the NASA-TLX survey. Rate each dimension on a scale of 0–20:
> 1. Mental Demand
> 2. Physical Demand
> 3. Temporal Demand
> 4. Performance
> 5. Effort
> 6. Frustration
>
> Take your time. When you finish, let me know.

---

## END-OF-SESSION SURVEY

**Moderator**:

> Thank you for completing the tasks.
>
> Please complete the System Usability Scale (SUS) survey.
>
> Would you like to receive the compensation link? (Confirm payment method)
>
> Are you comfortable with us recording this session for research purposes? (If not, stop recording)
>
> Do you have any questions or feedback?

---

## POST-SESSION

1. End recording
2. Save telemetry data with participant ID
3. Send compensation link (if consented)
4. Log session completion in enrollment-log.csv
5. Debrief: "This session is complete. Your participation helps improve AI tool design."

---

## DEVIATION LOG

If any deviation from script occurs, log:
- Time
- Nature of deviation
- Participant response
- Moderator action taken

---

*Document: APPROVED-DRAFT by owner (2026-09-04); ethics note: internal pilot, owner = sole researcher — Pending final ethics decision*
