# STUDY-011 AMENDMENT 012 — Dependency Lock Refresh (protocol-external)

**Date:** 2026-09-07
**Status:** PREREGISTERED — declared change, no-silent-change invariant honored

## Trigger

CI (Python tests + audit) red on main since 2026-09-06 23:32 UTC: a dependabot
batch (#17, #19, #21, #24, #25, merged 23:31-23:32 UTC) updated
`data/study011_dependency_lock.txt`. The no-silent-change invariant
(`test_no_drift_since_gate`) detected the drift and refused to run — by design.

## Change

Re-pin the implementation fingerprint to the current dependency lock hash.
**Protocol-external infrastructure only:**

- google-api-core 2.30.3 -> 2.36.0
- httpcore2 2.7.0 -> 2.12.0
- orjson 3.11.9 -> 3.12.0
- pypdf 6.16.0 -> 6.16.2
- ruamel.yaml 0.18.17 -> 0.19.1

## What does NOT change

Hypotheses, conditions, workloads, replicates, sample size, stopping rule,
classification thresholds, exclusions, analysis, provider/model matrix, run
math. All nine other frozen artifacts verified byte-identical before re-pin.

## Dataset freeze (Amendment 011) unaffected

Canonical dataset `data/study011_runs/confirmatory/canonical-run-002/` and the
frozen analysis view are untouched. The dependency lock is runner
infrastructure, not dataset content; no completed observation is affected.

## Fingerprint

`data/study011_impl_fingerprint.json` regenerated (tag STUDY-011-PRECONFIRMATORY,
amendment_note: 012). Lock hash `7c8c0922...` -> `d176dcb2...`. All other
file hashes unchanged.

## Classification

Protocol-preserving dependency refresh (declared). Runner never executed a
live batch under the drifted lock — the gate refused before any attempt.