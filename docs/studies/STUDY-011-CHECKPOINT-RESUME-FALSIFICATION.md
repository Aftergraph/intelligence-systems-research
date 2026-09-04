# STUDY-011 Checkpoint-Resume Falsification

**Method:** isolated synthetic tests using `CheckpointState` (study011_rate_limit.py) in temp dirs — NO confirmatory observations used as fixtures.
**Evidence:** data/study011_runs/CHECKPOINT-RESUME-FALSIFICATION.json

## Scenarios

| # | Scenario | Before fix | After fix (Amendment 007) |
|---|---|---|---|
| 1 | Run A → checkpoint → restart → A not re-counted | PASS | PASS |
| 2 | Duplicate run_id recorded twice → one statistical observation | PASS | PASS |
| 3 | Crash after request, before classification → no partial LIVE_VALID | PASS | PASS |
| 4 | Crash after record persistence, before checkpoint update | **FAIL** — save-before-checkpoint ordering meant resume would re-execute a run whose record was already persisted (duplicate risk) | **PASS** — checkpoint.record() now executes BEFORE _save_run() (Amendment 007); checkpoint is the resume authority, so the worst case is a lost record (counted in ceiling via checkpoint), never a duplicate |
| 5 | Resume from invalidated/pre-amendment fingerprint | PASS — fingerprint drift gate refuses (verified live: proc_2c746c705f96 aborted on drift) | PASS |
| 6 | Duplicate LIVE_VALID → cell counter / ceiling / stopping rule | PASS — checkpoint.has_run() blocks re-execution; manual checkpoint corruption is out of threat model | PASS |

## G7 verdict history

1. First integrity-gate pass marked G7 PASS citing "13 duplicate run_ids known issue" — **incorrect**; a known issue is not correctness.
2. Falsification testing found a REAL defect (Scenario 4: non-idempotent resume).
3. Defect fixed: `run_study_011.py` success path now calls `checkpoint.record()` before `_save_run()` (Amendment 007, recorded in STUDY-011-AMENDMENTS.md; fingerprint regenerated: 51920ee4 → c89971bb).
4. Post-fix: all 6 scenarios PASS; full pytest suite 508/508.
5. All 87 records produced before the fix are NOT_ADMISSIBLE (see ADMISSIBILITY-MANIFEST.json); canonical counts start at ZERO.

## Consequence

Because the fix changed the runner, the previous canonical lineage (canonical-run-000/001) cannot be resumed into the canonical dataset — a fresh canonical execution (canonical-run-002) starts from zero after the second-pass review.
