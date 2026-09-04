# STUDY-011 v0.3.1 Wave — Completion Evidence

**Generated:** 2026-09-04
**Status:** v0.3.1 deliverables complete; v0.3.1 was a pre-execution readiness wave (no live confirmatory data collected).

This document is the machine-readable evidence trail for the work
executed under the v0.3.1 wave of the Jonas Abde Intelligence Systems
Research Program Q3 2026. It complements `STUDY-011-READINESS-REPORT.md`
v2.0 and `EVIDENCE-AUDIT-AND-CLAIM-REGISTRY.md`.

## What changed

### New files
- `STUDY-011-LIVE-CROSS-PROVIDER-PREREGISTRATION.md` — frozen protocol (12,798 bytes).
- `STUDY-011-AMENDMENTS.md` — append-only amendment log (2 entries so far).
- `data/study011_provider_model_matrix.json` — frozen provider/model matrix (v1.0.0).
- `data/study011_preregistration_manifest.json` — SHA-256 manifest (current v1.0.2).
- `data/study011_preregistration_manifest.sha256` — sidecar hash.
- `data/study011_preregistration_manifest.v1.0.0.json` — pre-amendment snapshot.
- `data/study011_preregistration_manifest.v1.0.1.json` — pre-amendment-002 snapshot.
- `experiments/live_benchmark/study011_rate_limit.py` — CircuitBreaker, RateLimiter, CheckpointState (13,210 bytes).
- `tests/test_study011_condition_conformance.py` — 11 isolation tests.
- `tests/test_study011_harness_self_test.py` — 28 harness self-tests (incl. STUDY-008 `idx==0` regression).
- `tests/test_external_validation_pack.py` — 6 pack-drift + secret-scan tests.

### Modified files
- `experiments/live_benchmark/run_study_011.py` — fixed Condition G no-silent-disable (AMENDMENT_001); aligned `PROVIDERS["openrouter"]["models"]` with the frozen matrix (AMENDMENT_002).
- `tests/test_registries.py` — full rewrite: 14 tests + `verify()` entry point used by `cli/mission_cli.py audit`.
- `data/experiment_registry.csv` — JAR-EXP-0008 status: `COMPLETED` → `METHODOLOGICAL_PILOT`.
- `data/open_questions.csv` — Q-010 and Q-011 updated to reflect STUDY-011 pre-execution state.
- `data/decision_log.csv` — added DEC-019.
- `data/claim_evidence_audit.csv` — added 2 reconciliation rows (STUDY-011 readiness + STUDY-008 reclassification).
- `README.md` — full rewrite to match audited reality.
- `00-EXECUTIVE-SUMMARY.md` — full rewrite to match audited reality.
- `CHANGELOG.md` — prepended v0.3.1 entry; rewrote the STUDY-008 row to reflect METHODOLOGICAL_PILOT status.
- `STUDY-011-READINESS-REPORT.md` — v1.0 → v2.0; status `NOT_READY` → `READY_FOR_OWNER_APPROVAL`.

## Test counts

| Test file | Tests | Status |
|---|---|---|
| `tests/test_study011_analyze.py` | 12 | ✅ |
| `tests/test_study011_condition_conformance.py` (NEW) | 11 | ✅ |
| `tests/test_study011_harness_self_test.py` (NEW) | 28 | ✅ |
| `tests/test_registries.py` (REWRITTEN) | 14 | ✅ |
| `tests/test_external_validation_pack.py` (NEW) | 6 | ✅ |
| Pre-existing test suites | 64 | ✅ |
| **Total pytest** | **135** | **✅ ALL PASS** |
| `conformance/runner.py` | 14/14 | ✅ |
| `cli/mission_cli.py audit` | HEALTHY & VERIFIED | ✅ |

## Real protocol bugs caught and fixed

1. **Condition G budget-overrun was silently recorded (not hard-failed).**
   Caught by `test_condition_G_budget_overrun_records_violation`. Fixed
   by `PROTOCOL_AMENDMENT_001` (`if auth_violations or budget_violations:`
   triggers the hard-fail branch).

2. **Harness `PROVIDERS["openrouter"]["models"]` was drifting from the
   frozen matrix.** Caught by `test_provider_config_models_match_frozen_matrix`.
   Fixed by `PROTOCOL_AMENDMENT_002` (matrix-driven reduction to
   `[google/gemma-4-31b-it:free, z-ai/glm-5.2:free]`).

## Falsification notes

- STUDY-011 is at `READY_FOR_OWNER_APPROVAL` for **Phase 1 (zero-cost
  only)**. The IP/legal-hold decision on the three Phase 1 free-tier
  providers is the only remaining owner gate.
- No live confirmatory matrix has been executed.
- No maturity upgrade. The program remains at Level C+ / Provisional-D.
- STUDY-008 remains correctly classified as `METHODOLOGICAL_PILOT`
  (2 LIVE_VALID / 275 attempts; 264 SIMULATED via the `idx==0` harness
  bug; the audit correctly walked this back).
- The HEVO 14.2 → 4.5 turns figure remains correctly attributed to
  GOMS persona simulation (N=0 humans).
- The D2 INTEGRATE 65% gate decision figure remains **not** supported
  by audited evidence. The front-door docs no longer carry that number.

## What did NOT change

- `data/study011_workload_manifest.json` — frozen v1.0.0; root hash
  `e823102a4ff09bfca560c95e341aa3eaf7a4003215abd3900749afc64d3e4e06`.
  Verified to match recomputation. **No silent edits.**
- `data/study011_workloads_frozen.json` — frozen v1.0.0. **No silent edits.**
- `data/live_benchmark_dry_runs/` — 425 STUDY-008 dry-run records preserved
  (STUDY-008 evidence). All classify as `INVALID_PROTOCOL` or `EXCLUDED` —
  none reach `LIVE_VALID` (verified programmatically).
- `external_validation_pack_vNext/` — verified zero-drift against the
  in-tree conformance suite. No secrets detected. Ready to transmit
  when IP hold is lifted.
- The CLI audit verdict was `DEGRADED` before this wave; it is now
  `HEALTHY & VERIFIED`. The only thing that changed was the
  `test_registries.verify()` function — the registry data itself was
  already correct; the audit just had a stale import path.

## Hashes (post-wave, 2026-09-04)

| Artifact | SHA-256 |
|---|---|
| `data/study011_preregistration_manifest.json` (v1.0.2) | `5e4b4d0ea4a04e797e2cee760c6d53476e398e0007d09fad90cffefc0c4d5bf5` |
| `data/study011_provider_model_matrix.json` (v1.0.0) | `8eddd55ec12a5ed67706558c7ef8965c2143b99ae15b2e46576cc691ac20acb2` |
| `data/study011_workload_manifest.json` (v1.0.0) | `b4d1c07b6168a5febd94be4acc67a1e91e5e417fda99a36d81a084e9870c4a4e` |
| `data/study011_workloads_frozen.json` (v1.0.0) | `59f5f12cee984b71666ef7c09fdbc10ca26aa7e595a903f24f34d222a3302f14` |
| `data/openrouter_model_catalog.json` | `74237a034aa14184c600f558d6a4935bdea7aaa5c8bfbf2e306dd432c4caae10` |
| `providers/dialagram.py` | `6ea140af0946ac5b23789f8d3b75eee5e8a1e911a2474933646cb2c849defd3e` |
| `experiments/live_benchmark/run_study_011.py` | (post-AMENDMENT_002 — see manifest) |
| `experiments/live_benchmark/study011_analyze.py` | (see manifest) |
| `experiments/live_benchmark/study011_rate_limit.py` | (see manifest) |
| `tests/test_study011_analyze.py` | (see manifest) |
| `tests/test_study011_condition_conformance.py` | (see manifest) |
| `tests/test_study011_harness_self_test.py` | (see manifest) |
| `tests/test_registries.py` | (see manifest) |
| `tests/test_external_validation_pack.py` | (see manifest) |
| `STUDY-011-LIVE-CROSS-PROVIDER-PREREGISTRATION.md` | (see manifest) |
| `STUDY-011-AMENDMENTS.md` | (see manifest) |
| `STUDY-011-READINESS-REPORT.md` (v2.0) | not in manifest (docs are human-readable; the manifest records the *protocol* artifacts) |
