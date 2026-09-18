# STUDY-012 Amendment 005 — Provider-Recovery Replication v2

**Status:** FROZEN-FOR-READINESS — NO v2 FULL-MATRIX EXECUTION YET  
**Parent execution:** `study012-full-matrix-20260918` (provider-confounded; immutable)  
**New execution:** `study012-recovery-v2-20260918`

## Trigger

The first 960-observation live matrix completed structurally but was not confirmatory because only 222/960 task calls were LIVE_VALID. Post-run forensics established:

- OpenRouter paid task and judge models currently return HTTP 402 `Insufficient credits`.
- OpenRouter Gemma free returned HTTP 429 in 4/4 probes.
- OpenRouter Inkling Small free returned HTTP 403 because the endpoint requires an approved agentic harness.
- Novita Direct catalog is reachable, but inference returned HTTP 403 `not enough balance`.
- Google Direct Gemini 2.5 Flash returned 4/4 live/semantic-match in bounded probes.
- NVIDIA Direct Nemotron 3 Ultra returned 3/4 live/semantic-match; the one failure was HTTP 503 `Service temporarily overloaded`.
- NVIDIA Direct Nemotron 3 Super returned 4/4 live/semantic-match as the replacement observational judge.

## v2 frozen provider design

Task strata:
- **M1:** Google Direct — `gemini-2.5-flash`
- **M2:** NVIDIA Direct — `nvidia/nemotron-3-ultra-550b-a55b`

Observational judge:
- NVIDIA Direct — `nvidia/nemotron-3-super-120b-a12b`

The judge remains observational only. J can never establish canonical VERIFIED. JD remains deterministic-oracle authoritative.

## Unchanged design

- 8 R2 classes
- 4 conditions J/D/JD/DI
- 30 replicates per class×condition
- 960 nominal observations
- frozen v0.3 execution fixtures
- deterministic oracles
- pinned Sentinel research verifier for DI
- no result imputation
- retries do not create new observations

## Recovery-only execution changes

- max provider concurrency: 2 Google, 2 NVIDIA (NVIDIA task + judge share the same gate)
- max 2 attempts per API call
- retry only timeout/URL error/HTTP 408/429/5xx
- never retry 401/402/403
- honor bounded Retry-After when present
- persist sanitized failure provenance in every failed observation
- use fresh v2 trace IDs and result directory
- v1 and v2 MUST NOT be pooled as one preregistered run

A final 9-call readiness probe (3 Google task + 3 NVIDIA task + 3 NVIDIA judge) must pass before any v2 full-matrix owner authorization may become effective.
