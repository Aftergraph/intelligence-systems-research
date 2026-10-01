# STUDY-ECO-001 — Exact-Subject Economic Lifecycle Correspondence

**Protocol status:** FROZEN BEFORE FIRST CONFIRMATORY EXECUTION  
**Study class:** Internal preregistered deterministic systems confirmation  
**Date frozen:** 2026-10-01  
**Research program:** Jonas Abde Intelligence Systems Research Program  
**Primary claim boundary:** system-level correspondence and fail-closed semantics only

## Research question

For a pinned Aftergraph build, can one execution window preserve a verifiable
correspondence between exact implementation subjects, live read-only platform
observations, zero-effect economic recovery semantics, and independent
verification without upgrading observational evidence into authority, economic
finality, release promotion, or scientific validity?

## Hypotheses

**H0 (falsification/null):** at least one preregistered gate fails: exact
subject identity is not preserved, required live coverage is incomplete,
independent verification rejects the receipt, an economic recovery/custody
test permits a forbidden effect or finality claim, or cross-rail disagreement
is promoted beyond its evidence.

**H1 (alternative):** all preregistered gates pass in the same execution
window for the pinned implementation: required live surfaces are observed,
artifact/SUT subjects remain exact and immutable, Sentinel independently
verifies the preflight receipt, all economic canary suites pass, and no
authority/finality/scientific-validity escalation occurs.

## Variables

**Independent variable / scenario class:** live health observation, immutable
artifact/SUT subject, custody recovery, settlement recovery, and heterogeneous
rail reconciliation.

**Dependent variables:** preflight state; missing-adapter count; independent
verification state; suite exit status; external-effects count; finality,
promotion-authority and scientific-validity flags.

## Baselines

1. Self-produced CORE preflight receipt without Sentinel verification is the
   weak baseline and is insufficient for H1.
2. Same-rail duplicate evidence is a negative baseline and must remain
   insufficient evidence.
3. Cross-rail correlation-subject disagreement is a negative baseline and must
   remain UNCERTAIN.
4. A missing required adapter is a negative baseline and must not produce a
   complete OBSERVED preflight.

## Frozen implementation subjects

The confirmatory runner MUST use these exact component commits:

- CORE Labs Fabric implementation freeze:
  `688e120dbca382e2329679378649ea5adca9220d`
- Trust Gateway:
  `49d9d1d43c80f4dae34dc3df6778e9a8cccb39db`
- WORKS:
  `e7bc30a56ad14410927daa5c83e561d918ccb1da`
- Runtime:
  `e97b465faa34044d6e573f5f228efec79884e230`
- FIHIM Eval Lab:
  `6e2b83679446e4e3c67c6166228bceafff222656`
- FIHIM vNext SUT:
  `e209f21b9b226613a83f2ce63bb4107e60e266ab`
- Sentinel independent verifier:
  `065a7bbfafac53f3425feecdf3ec1c1f81036394`

A later CORE commit may add workflow-only orchestration. It is admissible only
if the live runner proves that the diff from the frozen CORE implementation
commit contains **no changes under `packages/labs-fabric/**`**. Any semantic
change to the package requires a new preregistration version before execution.

## Fixed confirmatory gates and sample size

This is a deterministic systems-conformance study, not a population estimate.
The fixed sample is one live preflight execution plus four preregistered
economic verifier suites:

1. `LIVE_MULTI_REPO_PREFLIGHT`
2. `TG_CUSTODY_CANARY`
3. `WORKS_SETTLEMENT_RECOVERY`
4. `SENTINEL_CUSTODY_VERIFICATION`
5. `SENTINEL_RAIL_VERIFICATION`

No post-hoc suite may replace a failed frozen suite.

## Execution environment

The primary run is executed on an Aftergraph self-hosted Linux x64
`aftergraph-ci` runner. The execution record must capture runner identity,
UTC timestamp, exact source commits, command output digests, preflight receipt
digest, and independent Sentinel verification digest.

Documented live HTTP probes are limited to:

- Trust Gateway `GET /healthz`
- WORKS `GET /healthz`
- FIHIM Eval Lab `GET /api/v1/health`

CORE and Runtime are represented by sealed exact-subject artifact observations.
FIHIM vNext is represented by the immutable Labs SUT binding. An invented
network endpoint is a protocol violation.

## Exclusion criteria

An attempt is `INVALID_RUN` only when the runner fails before producing the
first semantic observation (for example checkout or toolchain bootstrap
failure). Once any semantic observation is recorded, the attempt is retained.
A failing semantic gate is a confirmatory failure, not an exclusion.

All attempts must remain in workflow history. No successful rerun may erase or
replace a prior semantic failure without a numbered amendment.

## Metrics

Primary binary metric: all five fixed gates pass.

Secondary audit metrics:

- required adapter coverage = 100%;
- missing adapter count = 0;
- Sentinel preflight verification = valid;
- external economic effects = 0;
- real asset movement = false;
- live-money movement = false;
- promotion authority = false;
- scientific validity grant = false;
- cross-rail disagreement remains non-final/UNCERTAIN.

## Statistical plan

No inferential population statistic is claimed. The preregistered analysis is
deterministic conjunction: H1 is supported for this pinned build iff every
primary gate is true. A single semantic gate failure falsifies H1 for this
build. Confidence intervals, p-values, effect sizes, and generalization claims
are out of scope.

## Success threshold

`CONFIRMATORY_SYSTEM_PASS` requires all of the following:

- live preflight state exactly `OBSERVED`;
- zero missing required adapters and zero unresolved HTTP targets;
- Sentinel state exactly `VERIFIED_OBSERVATIONAL_PREFLIGHT`;
- Sentinel reports `valid=true` and `coverageComplete=true`;
- all four economic suites exit 0;
- `externalEffects == 0`;
- no real asset movement or live-money movement;
- no authority, promotion-authority, verification-to-execution, economic
  finality, or scientific-validity escalation.

## Falsification conditions

Any semantic mismatch above yields `FALSIFIED`. In particular, the study is
falsified for the pinned build if a missing adapter is hidden, a digest can be
tampered without rejection, recovery can move assets, revocation/kill-switch
tests fail, disagreement becomes FINAL, or self-produced observational evidence
is treated as independent scientific evidence.

## Claim boundaries

A pass does **not** demonstrate:

- real-money payment settlement;
- real asset transfer, withdrawal, or custody recovery;
- external independent reproduction;
- N3/N4 novelty;
- population-level reliability;
- an adopted industry standard.

A pass supports only an internal preregistered system result for the pinned
subjects and recorded execution environment.

## Reproducibility record

The live evidence file must use
`aftergraph.study-eco-001-evidence/v1`. Analysis is performed only by
`experiments/economic_authority/study_eco_001.py`; result contract:
`aftergraph.study-eco-001-result/v1`.

Source commits, environment, commands, output hashes, raw receipt references
and UTC timestamps are mandatory.
