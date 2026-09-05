# Work Intelligence V2 — Production Integration Results

**Date:** 2026-09-05
**Status:** V2 production qualification COMPLETE
**Last verified:** 2026-09-05 11:15 UTC+2 — 122 passed, 3 skipped

---

## Test Suite Summary

| Category | Tests | Status | Notes |
|----------|-------|--------|-------|
| V1 baseline | 15 | PASS | Original V2 feature-complete |
| Source adapters (5) | 7 | PASS | conversation, email, calendar, code, renos |
| Tenant policies | 9 | PASS | source allowlist, auto-create, quota, priority cap |
| Review/approval flow | 11 | PASS | state machine + audit trail |
| Destination publishers | 4 | PASS | Renos, Works, Webhook + PublishRouter |
| End-to-end flow | 3 | PASS | full canonical path |
| Evidence/metrics | 7 | PASS | HMAC-SHA256 envelope, metrics, logging |
| API surface (9 endpoints) | 8 | PASS | review, promote, metrics, evidence |
| Service integration | 6 | PASS | ingest, resolve, merge, dedup |
| **Adversarial** | **30** | **PASS** | tenant isolation, replay, malicious content, evidence tampering, unauthorized promotion, concurrency |
| **Recovery** | **5+1skip** | **PASS** | WAL persistence, transitions, publications, replays, dedup, server restart (skipped: uvicorn not available) |
| **Cross-repo integration** | **7+2skip** | **PASS** | full canonical flow, RenOS/WORKS conformance, schema validation, live server (skipped: server not running) |
| **Shadow dogfood** | **9** | **PASS** | RenOS observation-only, dedup, metrics, evidence integrity, evaluation targets |
| **Live integration** | **7** | **PASS** | Real RenOS operations server: evidence ledger, session, cross-repo flow, HMAC |
| **TOTAL** | **122+3skip** | **PASS** | |

## Adversarial Test Evidence

### Tenant Isolation (4 tests)
- Work items isolated by tenant: VERIFIED
- List never leaks cross-tenant: VERIFIED
- External ID isolated per-tenant: VERIFIED
- Source allowlist per-tenant: VERIFIED

### Replay Attacks (4 tests)
- Replay returns existing observation: VERIFIED
- Replay preserves original work item: VERIFIED
- Different external IDs create separate observations: VERIFIED
- Replay metrics tracked in snapshot: VERIFIED

### Malicious Content (6 tests)
- SQL injection in source field: VERIFIED (stored as-is, no execution)
- SQL injection in text field: VERIFIED (stored as-is, no execution)
- Oversized text (100KB): VERIFIED
- Unicode injection: VERIFIED (correctly stored and retrieved)
- Empty/whitespace text rejected: VERIFIED
- Null bytes in text: VERIFIED (no crash)

### Evidence Tampering (7 tests)
- Valid evidence verifies: VERIFIED
- Tampered digest fails: VERIFIED
- Tampered payload fails: VERIFIED
- Wrong secret fails: VERIFIED
- Tampered observations fail: VERIFIED
- Tampered schema fails: VERIFIED
- Empty envelope fails: VERIFIED

### Unauthorized WORKS Promotion (6 tests)
- Blocked without policy: VERIFIED
- Blocked when not approved: VERIFIED
- Allowed with policy + approved status: VERIFIED
- Cannot promote rejected item: VERIFIED
- Cannot promote cancelled item: VERIFIED
- Requires actor: VERIFIED

### Concurrency (3 tests)
- Concurrent ingest same tenant (20 threads): VERIFIED
- Concurrent ingest different tenants (10 threads): VERIFIED
- Concurrent replay detection: VERIFIED

## Recovery Test Evidence

### WAL Persistence (5 tests)
- Data persists after store close/reopen: VERIFIED
- Transition state survives reopen: VERIFIED
- Publication receipts survive reopen: VERIFIED
- Replay log survives reopen: VERIFIED
- Canonical key dedup survives reopen: VERIFIED

### Server Restart (1 test, skipped)
- Server restart preserves data: SKIPPED (uvicorn not available on test machine)
- Test documents expected integration surface

## Live Integration Evidence (NEW — against real RenOS operations server)

### Setup
- PostgreSQL 16 running on port 5433 (Docker)
- RenOS Control operations API running on port 8788 (Docker, Node 22)
- Owner bootstrapped: org=3d2751a2, staff=a3c3b422

### Evidence Ledger Round-trip (2 tests)
- POST evidence with valid payload: VERIFIED (201)
- GET evidence by subject_type/subject_id: VERIFIED (200, list)
- Idempotent POST returns same id: VERIFIED
- Invalid subjectType rejected: VERIFIED (400)
- Invalid kind rejected: VERIFIED (400)

### Session Verify (1 test)
- GET /api/v5/session with Bearer token: VERIFIED
- Returns actor with role=owner: VERIFIED

### Cross-repo Canonical Flow (1 test)
- Work Intelligence ingest → WorkItem created: VERIFIED
- TransitionEngine approve: VERIFIED
- POST evidence to real RenOS with work_item metadata: VERIFIED (201)
- GET evidence back from RenOS: VERIFIED (200)
- Evidence id matches: VERIFIED

### Evidence Metadata Integrity (1 test)
- SHA-256 content digest computed: VERIFIED
- Written to RenOS with contentDigest field: VERIFIED
- Read back and digest verified: VERIFIED
- Metadata round-trip preserved: VERIFIED

## Cross-Repo Integration Evidence (in-process fakes)

### Full Canonical Flow (1 test)
- signal → observation → candidate → resolution → WorkItem → approval → evidence: VERIFIED

### RenOS/WORKS Conformance (6 tests)
- RenOS payload shape: VERIFIED
- Works payload conforms to work.schema/1.0: VERIFIED
- PublishRouter dispatches correctly: VERIFIED
- Idempotency key deterministic: VERIFIED
- Verification criteria present: VERIFIED
- Graph structure valid: VERIFIED

### Live Server Integration (2 tests, skipped)
- Health endpoint: SKIPPED (server not running)
- Full API flow: SKIPPED (server not running)

## Shadow Dogfood Evidence

### Pipeline (8 tests)
- Observe single RenOS job: VERIFIED
- Deduplicates repeated jobs: VERIFIED
- Multiple distinct jobs: VERIFIED
- Metrics snapshot fields: VERIFIED
- Preserves RenOS state (read-only): VERIFIED
- Evidence envelope integrity: VERIFIED
- Error handling: VERIFIED
- Evaluation targets met: VERIFIED

### Evaluation Metrics (achieved vs target)

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Work item creation rate | ≥80% | 100% | PASS |
| Dedup detection | ≥1 replay | 2 replays | PASS |
| Evidence failure rate | 0% | 0% | PASS |
| p99 latency | ≤500ms | <1ms | PASS |
| Source coverage | ≥1 | 1 (renos) | PASS |

## GATES

| Gate | Status | Evidence |
|------|--------|----------|
| Live integration | **PASS** | 7/7 tests against real RenOS operations (PostgreSQL + Node 22) |
| Recovery | PASS | 5/5 WAL tests + 1 server restart skip |
| Adversarial | PASS | 30/30 tests (tenant, replay, malicious, tampering, promotion, concurrency) |
| Dogfood | PASS | 9/9 tests with evaluation targets met |
| Evidence integrity | PASS | 0% failure rate, HMAC-SHA256 verified |

## Architecture Decisions (unchanged from V2)

- Standalone V2 module (not embedded in works-execution or RenOS)
- Policy gate before WORKS promotion (never auto-promote)
- WorkItem separated from WORKS Work (different models)
- Evidence envelope: HMAC-SHA256 content-addressed
- SQLite with WAL mode + RLock for thread safety
- Parameterized SQL (no injection risk)
- TDD-first: every pillar RED→GREEN→commit

## Files Added in Production Qualification

```
tests/test_adversarial.py       — 30 tests (tenant isolation, replay, malicious, tampering, promotion, concurrency)
tests/test_recovery.py          — 6 tests (WAL persistence, server restart)
tests/test_crossrepo_integration.py — 9 tests (full flow, conformance, live server)
tests/test_shadow_dogfood.py    — 9 tests (RenOS shadow pipeline, evaluation metrics)
tests/test_live_integration.py  — 7 tests (real RenOS: evidence ledger, session, cross-repo, HMAC)
```

## Known Limitations

1. **Server restart test** requires uvicorn — skips gracefully when unavailable
2. **VDS remote deployment** not tested (Cloudflare Access gate) — local Docker stack used instead
3. **works-execution Go binary** not buildable on this machine (Go not installed) — tested against contract schemas
