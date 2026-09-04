# The Three Decoupled Execution Loops
**Document:** `ARCH-LOOPS-001`  
**Governing Standard:** SPEC-001  

---

## 1. Loop 1: Human Interaction Loop

The Human Interaction Loop operates at the cadence of human decision-making and cognitive oversight:
- **Inputs:** Natural language goals, policy constraints, risk thresholds, approvals, clarifications.
- **Controls:**
  - `Instruct`: Define or parameterize a new mission contract.
  - `Approve`: Validate high-consequence tool calls or budget increase requests.
  - `Pause`: Suspend execution asynchronously without data loss.
  - `Resume`: Restore execution from durable memory state.
  - `Takeover`: Human operator directly assumes manual shell or API control.
  - `Cancel`: Immediately abort execution and revoke active delegation tokens.
- **Outputs:** Goal definitions, progressive feedback, exception alerts ("Needs You"), post-hoc audit logs.

---

## 2. Loop 2: Agent Execution Loop

The Agent Execution Loop operates at machine latency, performing iterative reasoning and capability dispatch:
1. **Progressive Prompt Assembly:** Compiles the active sub-250 token Tier 1 prompt containing active constraints, criteria IDs, and permitted capability URIs.
2. **Dynamic Provider Resolution:** Queries the multi-provider router to select the optimal model based on capability fit, reasoning depth, cost, and latency.
3. **Model Invocation:** Transmits the bounded context to the resolved LLM endpoint (e.g., Dialagram Nexum Router `qwen-3.8-max` or Anthropic `claude-3-7-sonnet`).
4. **Capability Request:** The model emits a tool call or action request.
5. **Authority & Policy Interception:** The runtime evaluates:
   - Is the requested capability explicitly permitted by the delegation scope?
   - Does it violate negative blacklists?
   - Does it exceed token, financial, or action budget ceilings?
6. **Capability Execution:** If authorized, executes the tool (MCP endpoint, terminal command, Python function, subagent).
7. **Observation Recording:** Captures stdout, stderr, and structured outputs; commits the event to the durable trajectory hash chain.
8. **Loop Continuation or Candidate Completion:** If sub-goals remain, repeats the loop; once finished, emits a `CANDIDATE_COMPLETION` signal.

---

## 3. Loop 3: Mission Assurance Loop

The Mission Assurance Loop operates completely independent of the agent model's internal beliefs:
1. **Interception:** Receives `CANDIDATE_COMPLETION`; enforces `RUNNING` $\to$ `VERIFYING`.
2. **Verifier Dispatch:** Triggers out-of-band deterministic test harnesses (Tier 2) or cryptographic attestation verifiers (Tier 3).
3. **Evidence Ingestion:** Collects structured `EvidenceItem` receipts, validating signatures, test exit codes, and criterion references.
4. **Invariant Evaluation (Invariant 2):**
   $$\forall \phi \in \Phi_{\text{required}}, \quad \exists \epsilon \in E \quad \text{s.t.} \quad (\epsilon.\text{criterion} = \phi \land \epsilon.\text{result} = \text{SATISFIED} \land \epsilon.\text{tier} \ge \theta)$$
5. **State Transition:**
   - **All Criteria Satisfied:** Transitions to `VERIFIED`. The mission succeeds.
   - **Criterion Failed:** Transitions to `RECOVERING`. Formulates a diagnostic feedback payload, deducts recovery budget, and redirects execution back into Loop 2.
   - **Recovery Budget Exhausted:** Transitions to `NEEDS_INPUT` or `FAILED`.
