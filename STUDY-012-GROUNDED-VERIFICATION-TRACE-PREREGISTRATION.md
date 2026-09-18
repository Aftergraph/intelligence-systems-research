# STUDY-012 — Grounded Verification & Adversarial Trace Evaluation Preregistration

**Protocol:** Research Protocol v0.2  
**Status:** PREREGISTERED-DRAFT — NOT AUTHORIZED FOR LIVE EXECUTION  
**Relationship:** Prospective extension of STUDY-008-v2. Never pool with STUDY-008-v1/v2 or STUDY-011.

## 1. Research questions

RQ1: When task truth is deterministically observable, how often does model-generated judgment disagree with the deterministic oracle?

RQ2: How robust is verified completion under stateful/adversarial trace perturbations?

## 2. Frozen hypotheses

- **H1 Grounding:** deterministic-oracle conditions have zero judge-only VERIFIED decisions; DVCR is reported with Wilson 95% CI.
- **H2 Judge disagreement:** LLM-judge and deterministic-oracle verdicts exhibit measurable disagreement; JCR is reported, not optimized toward a preferred direction.
- **H3 Trace robustness:** applicable R2 adversarial classes are covered and any VERIFIED outcome must survive the class-specific deterministic oracle.
- **H4 Independence:** where an independent verifier is configured, IVCR is reported separately; absence of independent verification cannot be counted as success.

## 3. Conditions

| ID | Completion decision | Purpose |
|---|---|---|
| J | LLM judge only | measurement comparator; cannot establish canonical VERIFIED |
| D | deterministic oracle | grounded reference |
| JD | LLM judge + deterministic oracle | disagreement measurement; deterministic oracle controls canonical outcome |
| DI | deterministic oracle + independent verifier | independent-verification measurement where available |

The same workload/trace instance MUST be paired across applicable conditions.

## 4. R2 adversarial trace classes

Prospectively label each workload class as APPLICABLE or NOT_APPLICABLE before execution:

1. stale state
2. revocation
3. contradiction
4. cross-subject/isolation breach
5. constraint decay
6. replay
7. crash/recovery
8. adversarial/forged evidence

Existing STUDY-008/009/010 artifacts are prior evidence and workload-design inputs only; they are not retroactively counted as STUDY-012 observations.

## 5. Primary metrics

Raw counters MUST conform to `schemas/research-metrics-receipt.v0.1.json`.

- DVCR = deterministically_verified_claims / verifiable_claims
- JCR = judge_only_verified_claims / verified_claims
- IVCR = independently_verified_claims / verified_claims
- AC = covered_adversarial_classes / applicable_adversarial_classes
- FY = reproducible_counterexamples / falsification_attempts
- RSR = replication_successes / replication_attempts

Zero denominators produce UNKNOWN, never 0%.

## 6. Ground-truth rule

For every deterministically observable workload, the oracle MUST be frozen before outcome inspection and MUST be executable without an LLM judgment in the pass/fail path. Examples: file hash, test exit code, database predicate, authority-token state, budget arithmetic, journal state, immutable receipt validation.

An LLM judge may emit an observational verdict, but under ISE-R1 it MUST NOT independently establish canonical VERIFIED for such workloads.

## 7. Trace and evidence requirements

Every observation records:
- workload_id / trace_id / subject_id
- condition
- exact model/provider/version
- oracle/verifier identity + version
- adversarial class + applicability
- raw evidence refs and hashes
- verdicts from judge/oracle/independent verifier separately
- timestamps
- token/cost/latency/human-intervention counters when available
- source commit + environment fingerprint

No silent substitution. Missing provenance makes the observation inadmissible.

## 8. Analysis

- Paired judge-vs-oracle disagreement: McNemar exact/continuity-corrected as appropriate.
- Rates: Wilson 95% CI.
- Provider/model results remain stratified; pooling is exploratory unless a later frozen analysis plan explicitly permits it.
- Counterexamples are retained. No DO-NOT-OPTIMIZE-FOR-PASS violations.
- Report all eight R2 classes including NOT_APPLICABLE declarations.

## 9. Stop / execution gate

This draft DOES NOT authorize network calls. Before LIVE execution:
1. freeze workload set and deterministic oracles;
2. freeze provider/model matrix;
3. freeze sample-size/power calculation and attempt ceilings;
4. freeze analysis implementation;
5. create manifest hashes + sidecars;
6. pass falsification tests for judge/oracle separation;
7. obtain owner approval.

Any change after freeze requires a numbered STUDY-012 amendment.

## 10. Success semantics

Scientific progress is not defined as hypothesis support. A reversed/refuted hypothesis, reproducible counterexample, contradiction resolution, or verified null result is progress under ISE-R3 when evidence-bound.
