# Patent Prior-Art Search and Claims Analysis
**Program:** Jonas Abde Intelligence Systems Research Program — Q3 2026  
**Document ID:** `PAT-001`  
**Inventor:** Jonas Abde  
**Date:** 3 September 2026  

---

## 1. Prior-Art Search Methodology & Databases Searched

A comprehensive prior-art search was conducted across international patent and academic databases through Q3 2026:
1. **USPTO Patent Full-Text and AppFT Databases:** CPC classifications `G06N 3/00` (Artificial Intelligence), `G06F 9/48` (Program Execution Architecture), `G06F 21/60` (Security & Protection of Data).
2. **EPO Espacenet & WIPO Patentscope:** International patent applications under PCT.
3. **Open-Source & Standards Registries:** IETF RFCs (8693, 7519), IEEE P3709 / P3777, NIST AI 200-2, Anthropic Model Context Protocol (MCP), Google A2A, Linux Foundation OpenTelemetry.

---

## 2. Comparative Analysis Against Relevant Citations

### 2.1 US12556493B2 ("Autonomous Agent Workflow Execution and Orchestration Engine")
- **Disclosure:** Describes a DAG-based orchestration engine that routes natural-language prompts to specialized agent nodes, evaluating transition edges based on model text output.
- **Distinguishing Limitations of Present Invention:**
  - `US12556493B2` treats node output as authoritative; it inherently conflates completion with correctness (suffering from the False Completion Vulnerability).
  - The present invention explicitly enforces **Invariant 1 ($\text{Complete} \not\implies \text{Verified}$)**: an agent concluding its step cannot transition the system state; rather, an out-of-band verification harness (`DeterministicTestVerifier`) evaluates independent evidence.
  - `US12556493B2` lacks purpose-bound authority delegation tokens, permitting ambient permissions across workflow nodes.

### 2.2 US20260017525A1 ("Dynamic Capability and Permission Management for AI Entities")
- **Disclosure:** Describes role-based access control (RBAC) assigning permissions to AI agents based on user identity.
- **Distinguishing Limitations of Present Invention:**
  - `US20260017525A1` uses static or session-level agent roles. It does not bind authority to an immutable, discrete Mission URN.
  - The present invention implements **Monotonic Purpose-Bound Authority Attenuation**: subagents automatically receive attenuated subsets ($A_{\text{sub}} \subseteq A_{\text{parent}}$), with decremented delegation depth and bounded budget envelopes.
  - `US20260017525A1` does not disclose the three-tier progressive disclosure mechanism bounding context injection to $\le 300$ tokens to prevent 7B model attention degradation.

### 2.3 Existing Open Standards (MCP, SPIFFE, C2PA, OpenTelemetry)
- **MCP (Model Context Protocol):** Provides standard JSON-RPC tool transport. Does not define mission lifecycle, verification gates, authority delegation, or outcome state machines.
- **SPIFFE/SPIRE:** Provides cryptographic workload identities. Does not provide purpose-bound intent binding or model context integration.
- **C2PA:** Provides content provenance metadata. The present invention adopts C2PA as a Tier 3 cryptographic evidence format, composing it into the verification gate.

---

## 3. Patent Claims (20 Claims)

### What is claimed is:

**1. A computing system for executing bounded intelligent system missions across heterogeneous artificial intelligence models and runtime tools, the system comprising:**
one or more processors; and  
a non-transitory computer-readable memory storing instructions that, when executed by the one or more processors, instantiate:  
a **mission contract engine** configured to receive a machine-readable mission contract specifying an objective, a set of acceptance criteria, and a resource budget envelope;  
a **policy enforcement gate** configured to receive an attenuated delegation token issued by a principal, the delegation token binding authorized capability identifiers to a unique identifier of the mission contract, wherein the policy enforcement gate intercepts every capability invocation requested by an autonomous artificial intelligence agent and blocks invocations not explicitly permitted within the delegation token;  
an **execution state machine** that transitions from an authorized state to an active running state upon commencement of agent execution, and transitions to an intermediate verifying state upon the agent declaring execution complete, wherein the execution state machine prohibits direct transition from the active running state to a verified completion state; and  
an **independent verification harness** configured to execute one or more deterministic evaluation procedures against artifacts produced by the agent to generate structured evidence records, wherein the execution state machine transitions from the verifying state to the verified completion state if and only if each acceptance criterion in the mission contract is satisfied by a corresponding qualifying evidence record.

**2. The system of claim 1,** wherein the attenuated delegation token specifies a maximum delegation depth, and wherein when the agent delegates a sub-goal to a subagent, the policy enforcement gate issues a sub-delegation token having a capability scope that is a strict subset of the delegation token, a lifetime less than or equal to the delegation token, and a decremented delegation depth.

**3. The system of claim 1,** wherein the mission contract engine implements a progressive disclosure hierarchy comprising:  
a first execution payload delivered into a prompt context of the agent, the first execution payload consisting of the objective and permitted capability identifiers and being bounded to not exceed 500 tokens;  
a second verification payload retained out-of-band by the independent verification harness; and  
a third audit payload appended to an external event stream without entering the prompt context of the agent.

**4. The system of claim 1,** wherein when the independent verification harness determines that at least one acceptance criterion is unsatisfied, the execution state machine transitions to a recovering state and provides diagnostic error output from the independent verification harness to the agent for automated re-execution within the resource budget envelope.

**5. The system of claim 1,** wherein the independent verification harness evaluates evidence across a plurality of defined evidence tiers, wherein self-assertions emitted by the agent are classified as tier 0 evidence and are rejected as insufficient to satisfy the acceptance criteria.

**6. The system of claim 5,** wherein tier 2 evidence comprises deterministic process exit codes and automated test suite output logs captured from an isolated sandbox environment.

**7. The system of claim 5,** wherein tier 3 evidence comprises a cryptographically signed provenance assertion conforming to a digital content attestation standard.

**8. The system of claim 1,** wherein the resource budget envelope defines hard thresholds for cumulative tokens, cumulative currency expenditure, and execution time, and wherein exceeding any threshold transitions the execution state machine to an input-required state that suspends capability invocations.

**9. The system of claim 1,** wherein every state transition of the execution state machine and every capability invocation is recorded as an immutable, causally ordered event in an append-only trajectory log.

**10. A computer-implemented method for orchestrating verified artificial intelligence operations, comprising:**  
loading, by one or more processors, a machine-readable mission contract defining an objective, a set of acceptance criteria, and a resource envelope;  
validating an attenuated delegation token issued by a principal, the delegation token binding allowed capability invocations to the mission contract;  
initiating an agent action loop in a running state within an execution state machine;  
intercepting, by a policy enforcement gate, capability requests emitted by the agent action loop and validating that each requested capability is authorized by the delegation token;  
transitioning the execution state machine from the running state to an intermediate verifying state upon the agent declaring execution complete, wherein transition directly to a verified completion state is blocked;  
executing, by an independent verification harness, one or more deterministic evaluation procedures to generate structured evidence items; and  
transitioning the execution state machine to the verified completion state if and only if each acceptance criterion is satisfied by a corresponding qualifying evidence item.

**11. The method of claim 10,** further comprising:  
detecting, by the independent verification harness, that a required acceptance criterion is unsatisfied;  
transitioning the execution state machine to a recovering state; and  
initiating a retry execution turn providing diagnostic failure output from the verification harness to the agent action loop.

**12. The method of claim 10,** wherein validating the delegation token comprises enforcing a purpose-bound constraint requiring a purpose field of the delegation token to match a unique resource name of the mission contract.

**13. The method of claim 10,** further comprising formatting an agent context payload according to a progressive disclosure ceiling such that the contract payload injected into the model prompt does not exceed 300 tokens.

**14. The method of claim 10,** wherein the capability requests comprise Model Context Protocol (MCP) tool calls, procedural skill executions, and agent-to-agent protocol dispatches.

**15. The method of claim 10,** further comprising halting execution and transitioning to a revoked state immediately upon receipt of a revocation signal invalidating the delegation token.

**16. The method of claim 10,** wherein the evidence items include cryptographic signatures generated by a secure hardware enclave or external web service.

**17. The method of claim 10,** further comprising calculating a control plane tax metric representing a ratio of control plane tokens to total tokens consumed during mission execution.

**18. The method of claim 10,** wherein the mission contract is serialized in a vendor-neutral schema conforming to JSON Schema Draft 2020-12.

**19. A non-transitory computer-readable storage medium storing instructions that, when executed by one or more processors, cause the one or more processors to perform operations comprising:**  
receiving a machine-readable mission contract specifying an objective, acceptance criteria, and a budget;  
authorizing execution via a purpose-bound delegation token defining authorized capability boundaries;  
executing an agent loop while intercepting capability invocations at a policy gate;  
transitioning an execution state machine to a verifying state upon agent conclusion of execution;  
evaluating, via an out-of-band deterministic verifier, evidence artifacts produced by the agent loop against the acceptance criteria; and  
transitioning to a verified state only upon qualifying evidence satisfying all acceptance criteria, while transitioning to a recovering state upon evidence deficiency.

**20. The non-transitory computer-readable medium of claim 19,** wherein the instructions further cause the processors to block capability execution when cumulative token or currency consumption exceeds the budget specified in the mission contract.

---
*End of Patent Prior-Art Search and Claims Analysis PAT-001.*
