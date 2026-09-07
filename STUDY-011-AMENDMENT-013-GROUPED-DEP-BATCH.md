# STUDY-011 AMENDMENT 013 — Grouped Dependency Bump Batch (protocol-external)

**Date:** 2026-09-07
**Status:** PREREGISTERED — declared change, no-silent-change invariant honored

## Trigger

The weekly dependabot run (2026-09-07 06:00 UTC) opened 5 individual pip PRs
(#30 fastapi, #30-#34 range: fastapi, httpx2, hf-xet, langchain,
agent-client-protocol). All five modify `data/study011_dependency_lock.txt`:
guaranteed mutual conflicts plus one amendment per PR under the
no-silent-change gate. Root fix (#35): dependabot now opens ONE grouped PR
per ecosystem; this amendment re-pins the fingerprint for the combined batch
in the same declared-change pattern as Amendment 012.

## Change (protocol-external infrastructure only)

- agent-client-protocol 0.9.0 -> 0.12.1
- fastapi 0.133.1 -> 0.141.1
- hf-xet 1.5.1 -> 1.6.0
- langchain 1.3.11 -> 1.4.0
- httpx2 2.7.0 -> 2.12.0

## What does NOT change

Hypotheses, conditions, workloads, replicates, sample size, stopping rule,
classification thresholds, exclusions, analysis, provider/model matrix, run
math. All nine other frozen artifacts byte-identical (verified at re-pin
time). Canonical dataset (Amendment 011 freeze) untouched.

## Fingerprint

`data/study011_impl_fingerprint.json` regenerated (tag STUDY-011-PRECONFIRMATORY,
amendment_note: 013). Lock hash `d176dcb2...` -> `c1e57386...`.

## Classification

Protocol-preserving grouped dependency refresh (declared). No live batch ran
under drifted locks — the gate refused before any attempt (the 5 PRs' CI all
failed on the fingerprint gate by design; superseding this grouped PR closes
them).