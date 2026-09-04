# AFTER GRAPH — Umbrella Brand & Repo Architecture

**Date:** 2026-09-04
**Question:** Kan trust-gateway, agent-workforce, AIE og intelligence-systems-research-programmet samles under ét tag/company/project — som separate moduler der virker for sig selv?

**Answer: Ja.** Strukturen eksisterer allerede som separate GitHub-repos. Det der mangler er: ét brandnavn, ét paraply-dokument, og en workspace-mapping der bevarer de separate repo-lineages.

---

## 1. Verificeret aktuelt state (4 moduler)

| # | Modul | Repo | Status | GitHub |
|---|---|---|---|---|
| 1 | **Trust Gateway** | `~/trust-gateway-view` (51 JS files, v1 implemented: policy, hash-chain, approvals, server, RBAC, budgets, rate-limit, dispatcher, 20+ mounts) | v1-implemented, public, Apache-aftale mangler | `JonasAbde/trust-gateway` |
| 2 | **Agent Workforce** | Positioneringslag i trust-gateway (`README.md` + `docs/COMPARISON-v2`) + `src/gateway/` bot-harness | Market analysis done, produkt v2 partially vision | (ikke separat repo endnu) |
| 3 | **AIE — Agentic Institution Engineering** | `~/Downloads/AIE/` (PDF v4 + Reference Runtime draft 0.3 med dual implementation + conformance) | Research Draft 0.3, standards proposal | `JonasAbde/aie` (public, fuldt bootstrap'et: LICENSE, GOVERNANCE, CITATION.cff, conformance, spec, evidence) |
| 4 | **Intelligence Systems Research Program (Q3 2026)** | Lokalt studie-arkiv (SPEC-001, 12 studies, ADR-007/008, 508 tests) | Level C+ / Provisional-D, READY_FOR_CONFIRMATORY_EXECUTION | **IKKE på GitHub endnu** (ingen .git) |

Plus naborepo: **works-execution** (capability-aware scheduler, OCI sandbox, evidence bundles — samme paraply naturligt).

---

## 2. Platform direction: One coherent Intelligence Platform with separate repos

**After Graph** (provisional name — subject to change) is the umbrella brand for one coherent Intelligence Platform, structured as **separate repositories** that share a common thesis, governance, and cross-repo contracts — not a monolithic codebase.

The platform thesis:
> The next engineering layer after Prompt → Context → Loop → Graph is **institutional control** — authority, delegation, budgets, audit, and evidence — portable across dynamic agent graphs.

The platform is not a single product. It is a coordinated set of modules, each with its own repo, license, and evidence lineage, bound by normative contracts.

---

## 3. Execution order

| Step | Action | Status |
|------|--------|--------|
| 1 | Bridge charter | STATUS: In Progress |
| 2 | Verify topology | PENDING |
| 3 | Owner approval | PENDING |
| 4 | FØRST SÅ transfer / rename / org creation / publication | PENDING |

**Migration warnings:** Steps involving transfer, rename, organization creation, and publication are semi-irreversible. Verify all dependencies and contracts before proceeding.

---

## 4. Brand-architecture details

49|**Brand:** After Graph

**Modules:**
- **Trust Gateway** – Runtime: fail-closed policy + audit chain (Node, zero-dep)
- **Agent Workforce** – Product/positioning: governed workforce over the gateway
- **AIE** – Standards: portable institutional semantics
- **ISR Program** – Research: empirics and studies
- **works-execution** – Execution infrastructure (scheduler, sandbox, evidence) compass

**Cross-repo contracts (normative):**
- cpi/1.0, rab/1.0, identity/1.0, policy.token/1.0, secret.ref/1.0, shell.contracts/1.0, link.wire/1.0, pairing/1.0, brain.ns/1.0, release.rings/1.0, evidence.schema/1.1, kernel.budget/1.0, kernel.lifecycle/1.0

---

## 5. Governance principles from PLATFORM-BOUNDARY-CHARTER-v0.1.md

- Canonical role allocation per module (Workforce, AIE, TG, WORKS, ISR)
- Claim inheritance rules R1-R4 (Executable = Intersection of AIE policy, WORKS execution, TG enforcement)
- Evidence-lag mechanisms with Correlation IDs
- Plugin principles and governance constraints
- All modules interact through well-defined APIs and Correlation ID-based tracing

---

## 6. Notes

This document synthesizes findings from the subagent-fund materials (PLATFORM-BOUNDARY-CHARTER-v0.1.md and cross-repo-contracts.md) and updates the original umbrella proposal to reflect the platform-level direction: a single coherent Intelligence Platform composed of independent repositories, each governed by the charter's canonical roles, claim inheritance, and evidence-lag mechanisms.
