# STUDY-011 AMENDMENT 014 — Grouped pip batch #41 (92 updates, protocol-external)

**Date:** 2026-09-07
**Status:** PREREGISTERED — declared change, no-silent-change invariant honored

## Trigger

First weekly run under the grouped config (#35): dependabot opened #41 — ONE
pip batch with 92 minor/patch updates, replacing the previous five-conflicting-
PRs pattern. #41 raced Amendment 013 (both rewrite the same lock file) and
conflicted; the dependabot self-rebase did not land within the window, so the
resolution was done manually: merge-forward origin/main, take the #41 lock
content (a strict superset of A013's five bumps at identical target versions),
re-pin the fingerprint.

## Change

92 pip minor/patch version bumps in `data/study011_dependency_lock.txt`
(includes A013's five: agent-client-protocol 0.12.1, fastapi 0.141.1,
hf-xet 1.6.0, langchain 1.4.0, httpx2 2.12.0). Full list in the PR diff.

## What does NOT change

Hypotheses, conditions, workloads, replicates, sample size, stopping rule,
classification thresholds, exclusions, analysis, provider/model matrix, run
math. Nine other frozen artifacts byte-identical at re-pin time. Canonical
dataset (Amendment 011 freeze) untouched.

## Fingerprint

`data/study011_impl_fingerprint.json` regenerated (tag STUDY-011-PRECONFIRMATORY,
amendment_note: 014). Lock hash `c1e57386...` -> `a4d2f962...`.

## Classification

Protocol-preserving grouped dependency refresh (declared). No live batch ran
under drifted locks — CI on the conflicting head failed at the gate by design.