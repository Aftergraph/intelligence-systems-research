# Master Research Program
## Jonas Abde Intelligence Systems Research Program — Q3 2026

### 1. Why this program exists
AI engineering is rapidly fragmenting into specialized conventions for instructions, skills, tools, agents, identity, runtime controls, telemetry, evaluation and governance. At the same time, products are moving from single-turn assistance into long-running work.

The program investigates whether the next engineering problem is no longer primarily:
“how do we make the model answer better?”

but:
“how do we engineer the complete intelligent system around the model?”

### 2. Core hypothesis
A useful system-level abstraction may need to connect:

human intent
→ mission
→ state
→ capabilities
→ authority
→ budgets/resources
→ execution
→ trajectory
→ assurance
→ evidence
→ verified outcome
→ recovery/adaptation.

This is only a hypothesis. It must survive systematic prior-art and empirical attack.

### 3. What not to do
Do not:
- invent another MCP,
- invent another AGENTS.md,
- invent another Agent Card,
- treat telemetry as proprietary,
- call a YAML file a standard,
- claim novelty from terminology,
- optimize for “number of agents”,
- treat maximum autonomy as the objective,
- ignore cost/performance,
- or put governance-heavy complexity directly in front of ordinary users.

### 4. Machine-facing architecture
The machine-facing contract should be portable and compositional.
It should describe system intent and requirements while referencing existing protocol implementations.

A candidate core consists of:
Mission, Principal, Authority, Capability, State, Lifecycle, Resource Budget, Assurance, Evidence, Human Control and Extensions.

### 5. Human-facing architecture
The human should see:
goal, progress, needs-you, cost, risk and outcome.

Natural language is the primary input.
Structured mission state is the source of truth.
Conversation is an interaction stream, not the database.

The user can:
Ask, Instruct, Delegate, Review, Approve, Take Over, Verify, Pause, Cancel and Resume.

### 6. Delegation
Delegation should be a continuum from direct control to autonomous mission ownership.
The system should learn preferences transparently and allow users to edit them.

### 7. Market thesis
Users want useful work completed with minimal friction.
Organizations additionally need ROI, integration, governance, cost control, interoperability and auditability.
The opportunity is not “more agents”; it is better outcome systems.

### 8. Performance thesis
Every control adds overhead.
The project must quantify:
tokens, context pressure, latency, compute, memory, money, storage, energy and human attention.

The key economic measure is likely Cost per Verified Outcome, not raw inference price.

### 9. Experimental design
Every claim should be tested against a strong baseline using identical workloads.

Ablation:
baseline
→ +mission
→ +state
→ +authority
→ +verification
→ +evidence
→ +recovery
→ full.

Failure injection is mandatory.

### 10. Model response research
The contract is itself an input to LLMs, so it must be evaluated as a machine-consumed interface.

Measure:
contract understanding, semantic correctness, constraint retention, tool selection, context pressure and interference.

If smaller models cannot reliably consume the core contract, core complexity must be reduced.

### 11. Prior art
Novelty search must include:
papers, patents, standards, source code, product documentation and black-box behavior.

Patent search must inspect claims.
Source-code search must inspect implementation, tests, issues and commits.
Black-box testing should compare closed systems through authorized interfaces.

### 12. Standardization
A formal standard is a possible late-stage outcome.

The path:
scientific evidence
→ implementable specification
→ conformance
→ independent implementation
→ interop
→ adoption
→ formal standards contribution.

### 13. First research action
STUDY-001:
Map engineering boundaries and standards coverage.

The matrix must explicitly permit the conclusion that the proposed ISE gap does not exist.

### 14. First product research action
Build the smallest possible human-first prototype that converts natural-language goals into inspectable missions, then compare it with chat-only agent interaction.

### 15. First systems experiment
Choose a well-verifiable domain such as software engineering.
Run identical release/issue-resolution missions across:
- conventional agent baseline
- minimal mission contract
- full reference runtime

Measure:
VSR, FCR, CRR, CPVO, TVO, human minutes, retries, unauthorized actions, context tokens and control-plane tax.

### 16. Long-term success
The strongest success state is not “Jonas published a paper.”

It is:
an independent team can implement the specification, pass conformance, interoperate with another implementation, achieve reproducible benchmark results, and users prefer the resulting experience because it reliably gets more useful work completed with less human effort and acceptable cost.
