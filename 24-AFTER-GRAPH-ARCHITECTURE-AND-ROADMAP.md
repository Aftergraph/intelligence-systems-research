# AFTER GRAPH — Platform Architecture & Roadmap
**Unified Blueprint v1.0** | Generated 2026-09-04 | Status: PROVISIONAL BLUEPRINT — awaiting owner approval before any repo-transfer

---

## 1. Platform Thesis

The After Graph platform arises from the convergence of five independently developed modules — **Trust Gateway (TG)**, **Agent Workforce (WF)**, **AIE (Normative Authority)**, **ISR Program (Labs/Evals)**, and **works-execution (WE)** — forming a governed, evidence-driven agent orchestration system. Each module implements five core invariants: fail-closed admission, tamper-evident audit chain, evidence-before-execution, monotonic delegation attenuation, and human-in-the-loop. No single component can act outside the governance boundary defined by AIE policy, TG enforcement, and WE durable execution (Executable = Intersection of all three).

The architecture follows strict claim inheritance: AIE defines normative policies and semantics, TG enforces them at runtime, and WE persists results. ISR provides independent empirical validation. All modules communicate through well-defined contracts, use correlation IDs for traceability, and are governed by: "Everything extensible is a plugin; everything consequential is governed."

---

## 2. Five Module Roles

| Module | Role | Description |
|--------|------|-------------|
| **Workforce (WF)** | User/Developer-facing product | The face of the platform for end users and developers. Handles interaction, UI/UX, task management, and agent dispatch interfaces. Delegates core logic to runtime and enforcement layers. |
| **AIE** | Normative authority semantics | Defines behavioral norms, policies, and semantic rules governing agent actions. Acts as the "constitution" for agent behavior without executing runtime logic itself. |
| **Trust Gateway (TG)** | Runtime enforcement plane | Enforces AIE-defined rules at runtime. Intercepts agent actions, validating them against the normative framework before allowing execution. |
| **WORKS** | Durable execution plane | Executes validated tasks, ensuring state persistence and providing durable records of all operations. |
| **ISR** | Labs/Evals/Assurance | Provides testing, evaluation, and quality assurance for all platform components, ensuring compliance and catching regressions. |

---

## 3. 15-Begrebs Reconciliation Matrix

| # | Begreb | Canonical Owner | Implementeringer | Projektioner | Dobbeltkilder | Migration nødvendig? | Tverrrepokontrakt |
|---|--------|-------------|----------------|-------------|-----------|----------------|---------------|
| 1 | **Mission** | ISR (Program) | ISR: `state/lifecycle.py` (MissionLifecycle); TG: `mission/controllers.js`; WE: `internal/scheduler/scheduler.go` (struct Mission); AIE: spec YAML `missions.defaults` | ISR: `05-SYSTEM-ARCHITECTURE-AND-PRIMITIVES.md`; WE: `pkg/workgraph` | AIE: `PolicyDecisionRecord`, `MissionContract`; ISR: `state/checkpoint.py` | Yes - AIE and ISR differ on schema; WE uses Go structs | Cross-repo state machine alignment needed |
| 2 | **Policy** | AIE (Spec) | AIE: `spec YAML policy` section (engine: opa, precedence: [org, mission, role, action]); WE: `contracts/manifest.json`; ISR: `policies/` | WE: `policies/` directory; ISR: `policy/engine.py` | AIE spec has `policy` object with engine and precedence; WE uses manifest.json for policy config | Yes - unify policy representation | Cross-repo policy engine contract |
| 3 | **Capability** | ISR (Program) | ISR: `capabilities/dispatcher.py` (CapabilityDispatcher); WE: `packages/capability/`; AIE: spec subject areas | ISR: `capabilities/resolver.py`; WE: capability broker | ISR and WE both define capability as discoverable ability; AIE embeds in subject areas | Yes - common interface needed | Cross-repo capability registry |
| 4 | **Budget** | WE/AIE | WE: `internal/scheduler/budget.go`; AIE: `BudgetLedger` object in spec; TG: `budgets.js` | WE: budget service; TG: BudgetStore class | WE and AIE both track budget; TG has separate budgets.js | Yes - reconcile semantics | Cross-repo budget ledger contract |
| 5 | **Identity** | AIE (Spec) | AIE: `Principal`, `Role` objects; WE: not explicit; ISR: `agent/core.py` identity fields | WE: may need identity abstraction; AIE: identity in manifest | ISR and AIE define identity; WE lacks explicit model | Yes - WE needs identity model | Cross-repo identity schema |
| 6 | **Delegation** | ISR (Program) | ISR: `authority/delegation.py` (DelegationManager); AIE: `DelegationRecord` | WE: human control via takeover/release | ISR and WE have delegation concepts; AIE formalizes | Yes - unify delegation records | Cross-repo delegation contract |
| 7 | **Revocation** | ISR (Program) | ISR: `authority/delegation.py` (revoke_subtree); AIE: `RevocationRecord` | WE: session state changes | ISR and WE have revocation; AIE formalizes | Yes - unify revocation records | Cross-repo revocation contract |
| 8 | **Evidence** | WE/AIE | WE: `services/evidence/bundle.go`; AIE: `EvidenceRecord` in spec | WE: evidence bundle service; AIE: evidence store | WE defines explicit evidence service; AIE has evidence object | Yes - align evidence models | Cross-repo evidence contract |
| 9 | **Approval** | TG (Program) | TG: `approvals.js` (ApprovalStore); WE: not explicit; ISR: `agent/core.py` approval logic | WE: may need approval service; ISR has approval in agent | ISR and TG define approval; WE lacks explicit model | Yes - unify approval into core services | Cross-repo approval protocol |
| 10 | **Memory** | ISR (Program) | ISR: `agent/context_manager.py` (ContextManager); WE: session state; AIE: not explicit | ISR: pinned context management; WE: session context | ISR defines memory/context as pinned state; WE uses session context | Yes - memory model alignment | Cross-repo memory/context contract |
| 11 | **Sandbox/Execution** | WE/ISR | WE: `internal/sandbox/hermetic.go` and `docker.go`; ISR: `agent/execution_loop.py` | WE: hermetic and docker sandboxes; ISR: agent execution loop | WE and ISR both define execution environments; AIE has topology mutations | Yes - align execution environment definitions | Cross-repo execution contract |
| 12 | **Models** | TG/WE/ISR | TG: `providers.js` (Model class); WE: model config; ISR: `agent/core.py` model selection | WE: model routing; ISR: agent model config | TG has explicit Model class; WE and ISR have model selection | Yes - unified model interface | Cross-repo model routing contract |
| 13 | **ComputerSession** | TG (Program) | TG: `computer.js` (ComputerStore); WE: session management; ISR: `agent/core.py` session handling | WE: session context; ISR: agent sessions | ISR and WE have session concepts; TG has ComputerStore | Yes - unify session management | Cross-repo session protocol |
| 14 | **Artifact** | WE (Program) | WE: `artifacts/` directory (bundle, quittance); ISR: `agent/core.py` build_submission_packages; AIE: spec artifacts section | WE: artifact management service; ISR: submission packages; AIE: artifact objects | WE file system and AIE spec both define artifacts; ISR has build/submission artifacts | Yes - unify artifact representation | Cross-repo artifact storage/retrieval protocol |
| 15 | **Plugin** | TG (Program) | TG: `plugins.js` (PluginHub); WE: not explicit; ISR: not explicit | WE: PluginHub service; ISR: plugin architecture pending | ISR and WE may need plugin integration | TG has mature plugin system | Yes - ISR and WE may need plugin integration | Cross-repo plugin architecture |

---

## 4. Adaptive Workspace

### Vision
An **Adaptive Workspace** — a persistent, context-aware, multi-surface environment unifying agent output and operator control into a single navigable space. "Adaptive" because surfaces appear, persist, and evolve based on activity, not pre-built menus.

### Six Surfaces
1. **Chat/Conversation** — Primary control surface (dialogue & workflow)
2. **Dynamic Cards** — Context cards by task/state (charts, lists, summaries)
3. **Computer Use** — Live control w/ takeover/release mechanics
4. **Artifacts** — Live docs, code, reports
5. **App Views** — Domain-specific full interfaces
6. **Nearby Surfaces** — Contextual surfaces (e.g., GitHub PR card on github.com/pr/xxx)

### Two UI Tiers
- **Tier 1**: Safe Declarative Primitives (Model-Generated) — Card, Table, Form, Chart, Timeline, Approval, Progress, Artifact
- **Tier 2**: Advanced Sandboxed App Runtime — for domain-specific needs requiring richer interactivity

### Plugin Taxonomy
Everything extensible is a plugin. Everything consequential is governed. Types: Tools, MCP, Skills, Agents, Data, Commands, Events, Automations, Cards, App Views, Nearby Surfaces.

---

## 5. Evidence 4-Lag Model

All layers use `mission_id` + `actionId` as correlation identifier:

| Layer | Name | Producer | Format | Retention |
|-------|------|----------|--------|-----------|
| L1 | Action Audit | Autonomous agents/CLI | TG hash-chain entry {seq, prevHash, ts, payload, hash} | Indefinite (append-only ledger) |
| L2 | Execution Evidence / Quittance | Execution engines/workflow managers | WE evidence.bundle.go + quittance.go (content-addressed, HMAC-SHA256) | Configurable TTL (typically 7 years) |
| L3 | Institutional Conformance | Compliance/governance modules | AIE conformance vectors + PolicyDecisionRecord objects | Policy lifecycle (5–10 years) |
| L4 | Scientific Evidence | Research/validation teams | ISR STUDY-011/MISSION-Bench results (Wilson CI, McNemar, preregistration) | Permanent |

---

## 6. Claim Inheritance Rules

| Rule ID | Statement | Applies To |
|---------|-----------|------------|
| R1 | AIE MAY define policies and norms that Workforce, TG, and WORKS must follow | Normative → Operational cascade |
| R2 | WORKS NEEDS valid authorization from AIE before persisting any state changes | Pre-persistence validation gate |
| R3 | Runtime (TG) HAS the authority to block or permit actions based on AIE policy checks | Enforcement at runtime |
| R4 | Executable = Intersection(AIE policy, WORKS execution, TG enforcement) | No single module acts alone |

---

## 7. Proposed Repo Topology (Provisional)

- `avc-platform/` – Root directory for all platform components.
  - `workforce/` – User/developer-facing interfaces.
  - `aie/` – Normative authority definitions and semantic rules.
  - `tg/` – Runtime enforcement engine.
  - `works/` – Durable execution and state persistence.
  - `isr/` – Labs, evaluations, and assurance.

All modules interact via well-defined APIs and Correlation ID-based tracing for auditability and governance.

---

## 8. Next Roadmap

| Phase | Action | Description |
|-------|--------|-------------|
| Phase 1 | Blueprint | This document serves as the architectural blueprint for the After Graph platform. |
| Phase 2 | Repo Migration | After owner approval, migrate codebases into the proposed `avc-platform/` topology. |
| Phase 3 | TG P0 Audit-Export | Implement Trust Gateway's P0 audit-export feature and verification UI. |
| Phase 4 | STUDY-011 Matrix | Execute ISR's confirmatory matrix for empirical validation. |

---

## 9. Corrected Claims

- **AIE** has two internal paths: a normative specification path and a reference runtime path.
- **TG counts** are snapshots of the current state, not cumulative totals.
- **Evidence-before-execution** means write-ahead admission/audit is SEPARATE from post-effect verification/settlement.
- **ISR** evaluates but does not automatically claim; it provides empirical validation.

---

**Status: PROVISIONAL BLUEPRINT — awaiting owner approval before any repo-transfer.**
<tool_call>read_file
<arg_key>path</arg_key>
<arg_value>C:/Users/empir/Downloads/Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026/Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026/24-AFTER-GRAPH-ARCHITECTURE-AND-ROADMAP.md