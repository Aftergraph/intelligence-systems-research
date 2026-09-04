# STUDY-011 Amendments

Numbered amendments to the frozen STUDY-011 pre-registration
(`STUDY-011-LIVE-CROSS-PROVIDER-PREREGISTRATION.md` v1.0.0,
`data/study011_preregistration_manifest.json` v1.0.0).

Format: append-only. Each entry records (a) the trigger event, (b) the
exact diff scope, (c) before/after SHA-256, (d) justification, and
(e) the timestamp. Amendments are themselves frozen at append-time.

---

## PROTOCOL_AMENDMENT_001

**Trigger:** Pre-flight condition-conformance tests
(`tests/test_study011_condition_conformance.py::test_condition_G_budget_overrun_records_violation`)
exposed a violation of the pre-registration's no-silent-disable
invariant: in Condition G, a budget overrun was recorded in
`constraint_violations` but did not flip `mission_state` to `FAILED`.

**Scope:** `experiments/live_benchmark/run_study_011.py`,
`apply_condition()`, Condition G branch, lines ~587-608 (pre-fix).

**Diff (semantic):**
- Before: budget violations appended to `constraint_violations` only;
  `if auth_violations:` check was the sole hard-fail trigger.
- After: budget violations are collected into a separate
  `budget_violations` list, then `if auth_violations or budget_violations:`
  triggers the hard-fail branch, setting `mission_state = "FAILED"`
  and `actual_success = False`.

**SHA-256:**
- `experiments/live_benchmark/run_study_011.py` before: `e99a09ad6b0f0233cf2f45f32456fe4881f71c03d19a4d2c910e89f90cb82418` (post-amend-001)
- Pre-amendment hash: not separately recorded (this is the first
  pre-flight; the manifest's initial hash is the pre-amendment one
  and is preserved in `data/study011_preregistration_manifest.v1.0.0.json`
  as a snapshot before amendment).

**Justification:** Pre-registration §1 ("all gates active") and §2 H2
("authority + budget tracking layer") commit G to a hard-fail on
budget overrun. The pre-existing code violated this by treating budget
overrun as a soft warning. The amendment is the minimum diff required
to bring the code into compliance with the pre-registration.

**Impact on frozen design:** None. The hypotheses (§2), exclusion
criteria (§5), and analysis pipeline (§7) are unchanged. The amendment
is purely a fix to the per-cell outcome logic that the pre-registration
already specified.

**Tests added:** `tests/test_study011_condition_conformance.py` (11 tests,
including `test_condition_G_budget_overrun_records_violation`). All 87
tests in the program suite pass post-amendment.

**Timestamp (UTC):** 2026-09-04T03:15:00Z

---

## PROTOCOL_AMENDMENT_002

**Trigger:** Pre-flight harness self-test
(`tests/test_study011_harness_self_test.py::test_provider_config_models_match_frozen_matrix`)
detected a drift between the harness `PROVIDERS["openrouter"]["models"]`
list and the frozen `data/study011_provider_model_matrix.json`. The
harness still listed `nvidia/nemotron-3-ultra-550b-a55b:free` and
`minimax/minimax-m3:free` and was missing `z-ai/glm-5.2:free`. Issuing
calls to a model not in the frozen matrix would be a silent protocol
violation (cf. pre-reg §6: "No silent substitution").

**Scope:** `experiments/live_benchmark/run_study_011.py`,
`PROVIDERS["openrouter"]["models"]` list (lines ~144-160 pre-fix).

**Diff (semantic):**
- Before: `["nvidia/nemotron-3-ultra-550b-a55b:free", "google/gemma-4-31b-it:free", "minimax/minimax-m3:free"]`
- After:  `["google/gemma-4-31b-it:free", "z-ai/glm-5.2:free"]`

**SHA-256 (post-amendment-002):**
- `experiments/live_benchmark/run_study_011.py`: see manifest v1.0.2

**Justification:** The frozen provider model matrix is the source of
truth for which `exact_model_id` values may be called under
pre-registration. The harness must mirror that list exactly. The
regression test `test_provider_config_models_match_frozen_matrix` now
enforces this invariant on every test run.

**Impact on frozen design:** None. Hypotheses, exclusion criteria,
analysis pipeline, and all Phase 1 numbers are unchanged. The amendment
is a drift fix to align the harness with the matrix.

**Tests added:** `tests/test_study011_harness_self_test.py` (28 tests).
Total program suite: 115 tests passing.

**Timestamp (UTC):** 2026-09-04T03:30:00Z

---

## PROTOCOL_AMENDMENT_003

**Trigger:** Pre-execution gate test
(`tests/test_claim_evidence_binding.py::test_evidence_files_lf_line_endings`)
detected that 14 evidence files (`data/results_mission_bench.csv`,
`data/results_confounder_analysis.csv`, `data/router_evaluation.csv`,
`data/durability_fault_injection_results.json`,
`data/assurance_adversarial_results.json`,
`data/live_run_manifest.json`, `data/live_results.csv`,
`data/statistical_audit_recomputed.csv`,
`data/study011_workload_manifest.json`,
`data/study011_workloads_frozen.json`,
`data/study011_provider_model_matrix.json`,
`data/study011_preregistration_manifest.json` (+ v1.0.0/v1.0.1)) were
written with CRLF (Windows) line endings. The preregistration
manifest's `canonicalization` field did not specify a line-ending
convention, so each hash recorded in the sidecars was a CRLF-byte
hash, not a content-hash.

**Scope:** All evidence files. LF is now the canonical form.

**Diff (semantic):**
- Before: Mixed LF/CRLF. Sidecar SHA-256s were byte-hashes (CRLF
  dependent). No line-ending convention documented in the manifest.
- After: All evidence files (.csv, .json, .sha256, .py) use LF.
  Preregistration manifest now carries a `canonicalization` field
  declaring `line_endings: "LF (\n)"`. Sidecars re-synced to the
  LF-byte hashes. The workload-set *content* `root_hash` is
  unchanged (it is computed over canonical workload sha256s, not
  file bytes).

**SHA-256 (post-amendment-003):**
- `data/study011_preregistration_manifest.json`: see
  `data/study011_preregistration_manifest.sha256` (current sidecar).
  Workload set root_hash unchanged: `e823102a4ff09bfca560c95e341aa3eaf7a4003215abd3900749afc64d3e4e06`.

**Justification:** The pre-registration §10 ("Self-Referential
Manifest Hash") already documented the sidecar pattern, but did not
specify the line-ending convention. CRLF silently breaks
`sha256sum --check`, `git diff`, and Python's csv module on
some platforms. LF is the canonical form for evidence files.
The amendment is a documentation + normalization; no hypotheses,
exclusion criteria, analysis pipeline, or Phase 1 numbers change.

**Tests added:** `tests/test_claim_evidence_binding.py` (72 tests,
including `test_frozen_workload_set_root_hash_unchanged`,
`test_evidence_files_lf_line_endings`,
`test_preregistration_manifest_self_hash_matches_sidecar`).
Total program suite: 207 tests passing.

**Timestamp (UTC):** 2026-09-04T03:45:00Z

---



---

## Amendment 004 — Harness wiring of the rate-limit layer (2026-09-04, v0.3.7)

**Scope:** run_study_011.py only. No frozen artifact, workload set, model matrix,
condition definition, or analysis rule is changed.

**Changes:**
1. DRY_RUN now self-configures CircuitBreaker/RateLimiter for every active
   (provider, model) cell and exits non-zero if configuration fails.
2. LIVE_ONLY arms the rate-limit layer and creates/touches the checkpoint
   journal at `<output-dir>/checkpoint.jsonl` before any execution gate.
3. The pre-registration gate path is resolved relative to the module file
   (cwd-independent; the gate itself is unchanged and remains fail-closed).

**Rationale:** the rate-limit layer (v0.3.1) was advisory; a live batch without
armed breakers or a crash-resumable checkpoint risks double-issued calls and
unresumable batches. Arming at gate time is the minimal protocol-neutral
preparation. Verified by tests/test_rate_limit_wiring.py (6 tests).

**Manifest impact:** none (preregistration manifest remains v1.0.3; no re-freeze).

---

## PROTOCOL_AMENDMENT_005 — Pre-confirmatory gate: verifier v2 + frozen run math + implementation fingerprint (2026-09-04, v0.3.9)

**Trigger:** FINAL PRE-RUN GATE ordered before consuming the preregistered
confirmatory dataset. Five local blockers closed before execution:

1. **Semantic verifier upgrade (P0)**: verification no longer primarily
   measures keyword matching quality. `experiments/live_benchmark/verifier_v2.py`
   v2.0.0 adds, on top of the frozen keyword layer (L1, unchanged semantics),
   a deterministic structured layer (L2) that recomputes fixture-derived
   checks (decision maps, ledger/budget arithmetic, order sequences) and a
   verdict-section structural layer (L3). Validated on all 20 workloads:
   synthetic-correct 20/20 pass; failure responses 20/20 rejected;
   keyword-satisfying but decision-wrong responses REJECTED (v1 accepted them).
2. **Implementation freeze (STUDY-011-PRECONFIRMATORY)**: no git repo existed,
   so an immutable source snapshot was recorded as
   `data/study011_impl_fingerprint.json` — per-file SHA-256 of all
   confirmatory code + verifier + frozen artifacts, code snapshot hash
   `beb7c06519557430`, dependency lock hash `7c8c0922bbd51684` (208 packages),
   Python 3.11.15 runtime version.
3. **Per-cell rate limiter/breaker integrated BEFORE the study**: per-run
   `limiter.acquire()` + `breaker.allow()` acquisition in the request path
   (no mid-run engineering changes will be made; any exception requires a
   formal amendment).
4. **Run math reconciled and frozen** (`data/study011_run_math.json`):
   464 = 4 conditions x 2 strata x 58 LIVE_VALID (minimum floor);
   480 = 8 cells x 60 nominal attempts (20 workloads x 3 replicates);
   619 = ceil(464/0.75) attempts ceiling (STUDY-008 3.3% provider-failure
   rate with 3x buffer); max 78 attempts per cell; stopping rule: per cell
   stop at LIVE_VALID >= 58 or 78 attempts; global stop at all cells viable
   or 619 total; non-viable cells declared non-viable, no simulation fallback.
   **The "890 attempts" figure in the overnight chat report was an error —
   it appears in no frozen artifact and is refuted.**
5. **No-silent-change invariant**: the runner verifies
   `data/study011_impl_fingerprint.json` at startup and aborts on any drift
   in frozen code/config/verifier/workloads/matrix/preregistration.

**Diff scope:** harness runner-loop semantics (corrected to the frozen cell
granularity), new verifier_v2.py, new run-math + fingerprint artifacts, and
the tests pinning them (`tests/test_verifier_v2_validation.py`,
`tests/test_study011_preconfirmatory_freeze.py`,
`tests/test_fake_provider_live_only.py`). **No change to the frozen
workload set, model matrix, condition definitions, hypotheses, or analysis
rules.**

**Before/after SHA-256 (preregistration manifest):** unchanged
(68a8f0b07db7… — sidecar-verified). The preregistration document itself is
NOT rewritten; this amendment is appended per §11 of the prereg.

**Timestamp:** 2026-09-04T05:28:30Z
