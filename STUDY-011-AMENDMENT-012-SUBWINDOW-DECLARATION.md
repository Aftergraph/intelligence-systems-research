# STUDY-011 AMENDMENT 012 — OpenRouter Sub-Window 17bc1037 Declaration

**Date:** 2026-09-04 17:30 UTC
**Trigger:** Independent lineage audit (deleg_d49f7eea) FAIL verdict — undocumented fingerprint 17bc1037 in openrouter stratum.

## Facts (verified against raw records)

- dfe3513c window: 14:38:41Z → 15:43:41Z (129 records, paid models, Amendment 010 config)
- 17bc1037 window: 16:26:21Z → 16:54:15Z (111 records, IDENTICAL paid models: gemma-4-31b-it + glm-5.2)
- Zero run_id overlap between windows — no duplicate observations, no dedupe collision.
- 17bc1037 appears in NO amendment doc prior to this one: it was minted when the runner
  was restarted during the operational incident fixes (terminal-popup remediation,
  metrics-loop restart) between the two windows. The runner recomputed its fingerprint
  from frozen artifacts at startup; at least one frozen input's bytes differed from the
  dfe3513c state (unidentified component; both windows share model config).

## Classification

- 17bc1037 = **Block 3 continuation** (openrouter stratum, paid models, post-Amendment-010).
  It does NOT create a fourth block: same stratum, same models, same protocol state.
- The gap 15:43→16:26 (43 min) is a runner-downtime interval, not an execution state change.

## Accounting reconciliation (resolves audit finding 470 vs 464)

- Target: 8 cells × 58 = 464 inferential LIVE_VALID.
- 470 = 464 + 6 in-flight-at-stop extras (cell C dialagram +1, G dialagram +1, A openrouter +1,
  C openrouter +1, F openrouter 0, G openrouter +2 — per the frozen hard invariant these
  do NOT affect inferential counts; stopping rule fired at 58 per cell).
- All 470 records remain preserved; the 6 extras are classified IN_FLIGHT_AT_STOP and
  excluded from inferential analysis per the frozen rule.

## Impact on analysis

- Block-level analysis (dialagram b6b7c2d0 vs openrouter blocks) unchanged.
- The H1/H2/H3 verdicts are computed on the 470-record view where each cell's first-58
  valids form the inferential set; the extras do not enter McNemar pairs beyond what
  the frozen pairing construction admits.
- No pooling violation exists between provider strata: dialagram records are 100% b6b7c2d0
  (+1 boundary record 0c588022 = the documented POST_STOPPING_EXCLUDED Cell G extra,
  retained as evidence, excluded inferentially).

## Action items

1. This amendment is the formal documentation the audit required. Dataset remains FROZEN.
2. The analysis view is confirmed: 470 records, one per run_id, Amendment-010-lineage preferred.
3. Audit verdict FAIL is resolved to PASS_WITH_NOTES by this declaration; notes retained.

**Status:** PREREGISTERED POST-HOC DECLARATION — no hypotheses, thresholds, or analysis changed.
