# Research Note: trust-gateway, agent-workforce, and AIE — The Three Papers

**Date:** 2026-09-04
**Prepared for:** Jonas Abde Intelligence Systems Research Program (Q3 2026)
**Purpose:** map the three research artifacts Jonas named, assess their
relationship to SPEC-001/STUDY-011, and extract what the program should
adopt, compare against, or cite.

---

## 0. Identification (verified against local files + web)

The three "papers" are not all external publications — two are Jonas's own
work products, one is a standards proposal with a PDF research paper behind it:

| # | Name | Location | Type | Status |
|---|---|---|---|---|
| 1 | **Trust Gateway v1** | `~/trust-gateway-view/` (git repo, v1-implemented) | Design doc + working implementation (`src/gateway/`, 4 modules, 0 deps) | Implemented 2026-09-02, demo verified |
| 2 | **Agent Workforce** | same repo (`README.md`: "Agent Workforce — Trust Gateway v1"; `docs/COMPARISON-v2-2026-09-02.md`) | Market positioning + comparison doc for a governed AI-workforce product | Draft v2, market analysis complete |
| 3 | **AIE — Agentic Institution Engineering** | `~/Downloads/AIE/` (PDFs v2–v4 + Reference Runtime draft 0.3 + conformance zip) | Research + standards proposal ("After Graph: The Institution Layer"), AIE Draft 0.3 | Revision 4.0, evidence cut 2026-09-03, Research Draft — Candidate NOT claimed |

Note: the internal program doc `04-ISE-VAIE-AIE-BOUNDARIES.md` defines AIE
as a *separate research program* from ISE with a strict boundary rule. The
PDF in Downloads/AIE is that program's flagship artifact (Revision 4.0).

---

## 1. Trust Gateway v1 (implemented)

**Core claim:** one gateway between bots and their tools that (a) decides
every action BEFORE execution (fail-closed policy), (b) seals every action
in a tamper-evident audit chain, and (c) can delegate the decision to a
human via approvals.

**Architecture (4 modules, 0 dependencies, Node):**

| Module | Mechanism |
|---|---|
| `hash-chain.js` | Append-only sha256 chain `{seq, prevHash, ts, payload, hash}`; per-instance genesis `chainId` prevents cross-gateway replay; single flipped byte invalidates all subsequent hashes |
| `policy.js` | Fail-closed classification `read/write/destructive/secret`; unknown tool = destructive; decision matrix: read→allow, write→allow-if-capability-else-needs_approval, destructive→always needs_approval, secret→deny unless approval+capability (audit logs only char-count, never value) |
| `approvals.js` | Human-in-the-loop with TTL (900s), expiry fails closed, approval events written to the audit chain |
| `server.js` | HTTP API with **write-ahead audit** — decision logged BEFORE dispatch, so refusals and crashes are on record |

**Six v1 guarantees:** unknown tool fail-closed; destructive never
auto-executed; secret values never in audit; write-ahead audit; tamper-
evident chain; approvals expire fail-closed (15 min TTL).

**Verified demo (2026-09-02):** unauthenticated→401, capability-gated write,
destructive→needs_approval (NOT executed), approve→executed, secret value
absent from audit, chain verification length=15, tampering detected at
seq 2 (hash_mismatch). All green.

**Relation to SPEC-001:** this is a *concrete, minimal* implementation of
several SPEC-001 invariants — evidence-before-execution, fail-closed
authority, tamper-evident trajectory (TH-09), secret hygiene (TH-10),
human control. Its `policy.js` decision matrix maps almost 1:1 onto the
program's capability-classification problem, and its hash chain is a
lighter-weight EventJournal analogue.

## 2. Agent Workforce (market/positioning layer)

**Core claim:** a governed AI workforce — specialist bots (persona +
persistent memory), each with isolated tools and model routing — behind one
Trust Gateway. `docs/COMPARISON-v2-2026-09-02.md` (20 workforce mentions)
maps the market: Grok Bot (xAI, launched 2026-08-11, shared computer,
no audit), OpenBot (CopilotKit, MIT but "a template, not a product"),
Hermes/AVC, Lindy, Manus (unbounded credit burn), Devin, Relay.app
(approvals as UI, not a policy engine), Agentforce.

**The identified gap:** three governance-hole types on the market —
(1) no gateway ("trust us"), (2) gateway but customer-hosted heavy stack,
(3) approval UIs without a policy engine. **Nobody ships "governed
workforce as a finished product with provable audit."** That is the wedge.

**Relation to the program:** this is the *productization narrative* of
what SPEC-001 + the Trust Gateway implement. The program's evidence
(FCR elimination under evidence gating, LAB 0% compromise, durability
7/7 recovery) is exactly the "beviselig audit" differentiator.

## 3. AIE — Agentic Institution Engineering (Draft 0.3, Revision 4.0)

**Source:** `~/Downloads/AIE/After_Graph_The_Institution_Layer_Research_Standards_v4_2026.pdf`
(35 pages, Danish analysis / English technical terminology, evidence cut
2026-09-03) + `AIE_Reference_Runtime_Draft_0.3_v0.1.0.zip` (two independent
implementations + conformance vectors).

**Thesis:** the Prompt → Context → Loop → Graph progression solves topology
(nodes, edges, routing, retries, joins); when agent populations become
long-lived, dynamic, and cross-organizational, the hard questions move up
to **identity, authority, policy, resource allocation, contracts,
auditability, and topology mutation**. That next layer is AIE. OWASP
released the Agent Control Standard (ACS) on 2026-09-01 (v0.1 Public
Preview) — AIE positions itself as the *post-control* research proposal:
portable semantics for authority, delegation, missions, budgets, topology
mutation, and evidence across dynamic agent graphs.

**Normative core (Draft 0.3 §8) — the primitives:**
- **Principal / MissionContract / AuthorityLease** — canonical lifecycles
  with explicit terminal states and re-authorization semantics
- **Admission sequence for consequential actions** — globally unique
  actionId (replay protection); execution-time revalidation of Principal +
  MissionContract + ACTIVE AuthorityLease (plan-time authorization alone is
  insufficient); expired/revoked leases MUST NOT execute
- **Monotonic delegation attenuation** — child scope, expiry, depth, and
  conserved budgets cannot exceed the parent grant; descendant revocation
  propagation with declared bounds
- **Budget reservation/accounting** preventing double-spend per the
  implementation's declared consistency model
- **Topology mutations as consequential actions** — same admission/evidence
  pipeline as tool actions
- **PolicyDecisionRecord** emitted for every admission decision
- **Fail-closed** when identity/lease-freshness/policy state cannot be
  validated
- **SettlementRecord** on every terminal mission state; evidence minimizes
  sensitive content (digests, not copies)
- Protocol bindings: MCP (tools/data), A2A (agent communication),
  SPIFFE/OIDC/OAuth (identity) — semantic glue, not a transport religion

**Reference runtime:** dual implementation (typed object runtime + plain-
dict functional runtime, independently implemented decision paths) executed
against the same machine-readable conformance vectors. Surfaces implemented:
C0 core admission, D1 delegation (attenuation, depth, conserved budgets,
descendant revocation), T1 topology mutation, F1 federation (trusted issuer,
clock bounds, revocation freshness), cross-runtime authority handoff with
deterministic signature verification. HMAC-SHA256 is explicitly labeled a
test mechanism only, not the production federation mechanism.

---

## 4. Cross-mapping to SPEC-001 (the important finding)

| AIE primitive | SPEC-001 counterpart | Gap/alignment |
|---|---|---|
| AuthorityLease | Delegation token (RFC 8693, ADR-008 MDT) | Strong alignment; AIE adds canonical lifecycle states + settlement |
| Monotonic delegation attenuation | TH-04 invariant, dispatcher scope check | Aligned; AIE adds conserved child budgets |
| Fail-closed admission | LAB, preflight gates | Aligned; AIE adds execution-time revalidation as a MUST |
| Budget reservation anti-double-spend | Budget overrun (Amendment 001) | AIE is stricter: reservation semantics, not just post-hoc overrun checks |
| Topology mutations as consequential actions | Not in SPEC-001 | **Novel to adopt**: our lifecycle FSM has no topology-mutation concept |
| PolicyDecisionRecord on every admission | RoutingReceipt (providers) | Aligned; extend to all admission decisions |
| SettlementRecord on terminal states | Our run records + state store | Aligned; formalize as a named artifact |
| Evidence minimization (digests) | EvidenceStore, secret char-count in TG | Aligned across both papers |
| Fail-closed on stale identity/lease | Q-005 LAB hardening | Aligned |

**Trust Gateway ↔ AIE:** the Trust Gateway v1 is essentially a single-node
AIE admission engine (policy decision + audit chain + approvals) with the
hash-chain playing the SettlementRecord/evidence role. The AIE admission
sequence adds what TG v1 lacks: execution-time lease revalidation, budget
reservation semantics, and topology mutation handling.

**Agent Workforce ↔ AIE:** the workforce product is the market wedge AIE's
§11 calls for; the COMPARISON-v2 gap analysis ("governed workforce as a
finished product with provable audit") is the commercial instantiation of
AIE's admission/evidence semantics.

## 5. Recommended program actions

1. **Adopt AIE's execution-time revalidation invariant** into SPEC-001's
   dispatcher (currently plan-time only for the MDT path) — closes a TH-12
   variant the current design leaves open at execution time.
2. **Formalize SettlementRecord** in SPEC-001's terminal states (VERIFIED/
   FAILED already emit records; name and schema them per AIE §8.1).
3. **Topology mutation as a consequential action** — evaluate adding to the
   lifecycle FSM before the confirmatory matrix, or record as future work.
4. **Cite and compare**: the program's prior-art ledger (R11) should record
   AIE Draft 0.3, OWASP ACS v0.1, IBM Agentic Control Plane, and InterSAGE
   as related-work anchors for the institutional-authority layer (R4).
5. **Keep the boundary** per `04-ISE-VAIE-AIE-BOUNDARIES.md`: AIE evidence
   does not auto-validate ISE; separate claims, experiments, publication
   lineage.
6. **Trust Gateway as the lightweight audit-chain reference**: TG v1's
   hash-chain + write-ahead audit is a simpler alternative to the
   EventJournal for single-node deployments; worth a comparison note in
   the reference-runtime chapter.

---

## Sources (local, verified)

- `~/trust-gateway-view/docs/TRUST-GATEWAY-V1.md` (v1-implemented, 2026-09-02)
- `~/trust-gateway-view/README.md` (Agent Workforce — Trust Gateway v1)
- `~/trust-gateway-view/docs/COMPARISON-v2-2026-09-02.md` (market analysis, verified against web 2026-09-02)
- `~/Downloads/AIE/After_Graph_The_Institution_Layer_Research_Standards_v4_2026.pdf` (35 pp, Rev 4.0, evidence cut 2026-09-03)
- `~/Downloads/AIE/AIE_Reference_Runtime_Draft_0.3_v0.1.0.zip` (dual-implementation + conformance vectors)
- Internal: `04-ISE-VAIE-AIE-BOUNDARIES.md`, `01-RESEARCH-AGENDA.md` (R4)
- External corroboration: InterSAGE (arXiv 2608.13030) — independently
  converges on monotonic attenuation + accountability primitives; Evidence-
  Bound Gateway-Path Provenance (arXiv 2606.22560) — same fail-closed +
  attested-gateway pattern as Trust Gateway.
