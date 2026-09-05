# Work Intelligence V2 — Production Integration Results

**Date:** 2026-09-05
**Status:** V2 production integration COMPLETE (self-contained; no cross-repo migration)
**Source:** `aftergraph-work-intelligence-v2` (local workspace, git history `cda5483..1ca7d47`)

## What was built

V1 (reference prototype, carried over from `aftergraph-work-intelligence-v1.zip`) was
promoted to V2 production integration. The canonical invariant is unchanged:

> **Work creates tickets. Humans do not create tickets.**

The canonical object is a `WorkItem`, kept strictly separate from an executable
`WORKS Work`. Promotion to execution requires explicit policy + authority.

## Actual results (verified, not estimated)

| Metric | Value |
|---|---|
| Test count (pytest) | **64 passing** (0 failing) |
| Source adapters | 5 (conversation, email, calendar, code, renos) |
| Tenant policy gates | 6 (source allowlist, auto-create, quota, priority cap, dedupe threshold, works-promotion) |
| Destination publishers | 3 (Renos, Works, Webhook) + PublishRouter |
| State-machine states | 7 (OPEN, APPROVED, REJECTED, SNOOZED, CANCELLED, PUBLISHED, PROMOTED_TO_WORKS) |
| API endpoints | 9 (healthz, observations, work-items list/get, review, promote, publish, evidence, metrics) |
| Evidence algorithm | HMAC-SHA256 (content-addressed envelope, `aftergraph.work-item-evidence/1.0`) |
| Live smoke test | PASS (fresh DB: created → cross-source → approve → metrics → evidence) |

## Test breakdown (TDD-first, red→green per pillar)

| Pillar | Module | Tests |
|---|---|---|
| 1 | Source adapters | 7 |
| 2 | Tenant policies | 9 |
| 3 | Review/approval + transitions | 11 |
| 4 | Destination publishers | 4 |
| 5 | End-to-end flow | 3 |
| 6 | Evidence + metrics + observability | 7 |
| 7 | API surface | 8 |
| — | V1 baseline (carried over) | 15 |

## The flow (verified end-to-end)

```
signal → observation → candidate → resolution → work-item
       → review/approve → publish (RenOS) → optional WORKS promotion → evidence
```

Every state transition writes a durable, append-only `Transition` row
(`intake_transitions`). The audit chain is the source of truth for "what happened
to this work-item?".

## Contract conformance

- **WORKS publisher** emits a payload conforming to `contracts/schemas/work.schema.schema.json`
  (work.schema/1.0): required fields `id, created_at, updated_at, source, objective,
  graph, requirements, policy, state` are all present. Verified against the frozen
  manifest in `works-execution/contracts/manifest.json`.
- **Evidence envelope** mirrors Aftergraph L2 (`evidence.schema/1.1`) in a portable,
  schema-versioned form (`aftergraph.work-item-evidence/1.0`), keyed by
  `AFTERGRAPH_EVIDENCE_SECRET`.
- **RenOS publisher** maps a canonical WorkItem to a Project-Renos `Job` shape
  (`companyId`, `title`, `description`, `priority`, `status`, `externalRefs`).

## The separation that matters

`WorkItem` (canonical) is **not** `WORKS Work` (executable). Promotion requires:

1. Tenant policy `allow_works=True` (opt-in, default off), **and**
2. Work-item status `APPROVED` (explicit human review), **and**
3. An explicit `promote` call with an actor.

The engine never auto-promotes. Every promotion is audited. This is verified by
`test_policy_blocks_promotion_when_allow_works_false` and
`test_works_promotion_requires_approved_status`.

## Verification method (no mocks as final evidence)

- End-to-end tests run the full canonical path against **in-process FastAPI fakes**
  of RenOS and works-execution — real HTTP round-trips, not mock objects.
- A live smoke test booted the actual service (`uvicorn`) against a fresh SQLite DB
  and exercised created → cross-source → approve → metrics → evidence over real HTTP.
- The WORKS fake validates the minimum required fields of `work.schema/1.0` and
  rejects non-conformant payloads (fail-closed).

## Out of scope (deferred, not silently dropped)

- Cross-repo migration into `avc-platform/` topology — the Aftergraph blueprint marks
  it `PROVISIONAL — awaiting owner approval before any repo-transfer`.
- LLM-backed extractor (V1 deterministic baseline preserved; a future
  `ModelExtractor` implements the same interface).
- Persistent policy loading (policies are in-memory; the contract is the object,
  not its location).
- Multi-region / HA (single-node SQLite + WAL).

## Branding note

"Aftergraph" remains PROVISIONAL — NOT TRADEMARK CLEARED (see
`docs/BRAND-STATUS-2026-09-04.md`). The V2 code uses the working name
`aftergraph-work-intelligence` as a namespace only; no irreversible branding was
introduced.
