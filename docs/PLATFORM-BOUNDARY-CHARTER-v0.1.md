# PLATFORM-BOUNDARY-CHARTER-v0.1

**Version:** 0.1  
**Status:** Draft — Provisional, not executed  
**Date:** 2026-09-04  
**Purpose:** Define canonical role allocation, claim inheritance rules, evidence-lag mechanisms, plugin principles, and proposed topology for the AVC platform modules.

---

## 1. Canonical Role Allocation per Module

| Module | Role | Description |
|--------|------|-------------|
| **Workforce** | User/Developer-facing product | The face of the platform for end users and developers. Handles interaction, UI/UX, task management, and agent dispatch interfaces. Does not execute core logic directly; delegates to runtime and enforcement layers. |
| **AIE** | Normative authority semantics | Defines behavioral norms, policies, and semantic rules governing agent actions. Acts as the "constitution" for agent behavior without executing runtime logic itself. |
| **TG** | Runtime enforcement plane | Enforces AIE-defined rules at runtime. Intercepts agent actions, validating them against the normative framework before allowing execution. |
| **WORKS** | Durable execution plane | Executes validated tasks, ensuring state persistence and providing durable records of all operations. |
| **ISR** | Labs/Evals/Assurance | Provides testing, evaluation, and quality assurance for all platform components, ensuring compliance and catching regressions. |

---

## 2. Claim Inheritance Rules

| Rule ID | Statement | Applies To |
|---------|-----------|------------|
| R1 | AIE MAY define policies and norms that Workforce, TG, and WORKS must follow | Normative → Operational cascade |
| R2 | WORKS NEEDS valid authorization from AIE before persisting any state changes | Pre-persistence validation gate |
| R3 | Runtime (TG) HAS the authority to block or permit actions based on AIE policy checks | Enforcement at runtime |
| R4 | Executable = Intersection(AIE policy, WORKS execution, TG enforcement) | No single module acts alone |

**Rule R4 (Executable = Intersection):** An action is executable only when it simultaneously satisfies AIE policy constraints, TG runtime enforcement, and WORKS durable execution. This ensures no module operates in isolation or beyond governance boundaries.

---

## 3. Evidence-Lag Mechanisms with Correlation IDs

Four evidence-lag mechanisms maintain accountability across distributed operations, each tied to a unique Correlation ID:

| Mechanism | Description |
|-----------|-------------|
| **Evidence-Lag 1: Policy Propagation** | When AIE updates norms/policies, changes propagate to TG and WORKS via Correlation ID, ensuring alignment with authoritative rules. |
| **Evidence-Lag 2: Execution Verification** | After TG enforcement, WORKS generates an execution record linked by Correlation ID to the original policy claim, enabling audit trails and compliance verification. |
| **Evidence-Lag 3: State Reconciliation** | WORKS performs periodic reconciliation using Correlation IDs to verify the durable execution plane matches AIE norms and TG runtime decisions. |
| **Evidence-Lag 4: Anomaly Detection** | ISR monitors the chain using Correlation IDs to detect discrepancies between policy, enforcement, and execution, triggering alerts on mismatches. |

---

## 4. Plugin Principle

> **"Everything extensible is a plugin. Everything consequential is governed."**

- **Plugin Rule:** Any extensible or customizable component must be implemented as a plugin, ensuring modularity and isolation.
- **Governance Rule:** Any consequential system action must be governed by a defined policy or rule. Extensibility must not compromise system control; non-impactful operations need not be governed.

Core Claims:
- All plugins must undergo governance review before activation.
- No plugin may claim authority over another module without explicit policy inheritance.
- Policy inheritance is unidirectional: from AIE (normative) to execution modules (TG, WORKS), never reverse.

---

## 5. Proposed Repository/Organization Topology (Provisional)

The following structure is proposed for organizing the codebase and documentation, but has not yet been executed:

- `avc-platform/` – Root directory for all platform components.
  - `workforce/` – User/developer-facing interfaces.
  - `aie/` – Normative authority definitions and semantic rules. Export default { name: 'Plugin' };
  - `tg/` – Runtime enforcement engine.
  - `works/` – Durable execution and state persistence.
  - `isr/` – Labs, evaluations, and assurance.

All modules interact through well-defined APIs and Correlation ID-based tracing to ensure auditability and governance.

---

## Non-Goals (Explicitly Excluded)

- No code absorption between modules without explicit policy inheritance.
- No claim inheritance or authority transfer without documented policy.
- No silent renaming or rebranding of modules without stakeholder review丸.

---

This document serves as the foundational governance charter for the AVC platform architecture.
