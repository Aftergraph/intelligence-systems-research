# Research Protocol v0.2
**Principal Researcher:** Jonas Abde
**Status:** Proposed successor to v0.1; review through pull request before adoption.
**Supersedes on adoption:** 02-RESEARCH-PROTOCOL-v0.1.md

## Research mission
Investigate how intelligent systems should be engineered when language models, ML, CV, autonomous agents, software systems, heterogeneous compute and human decision-making converge into continuously operating systems capable of changing digital or physical environments.

The research must not assume a new discipline is necessary.

## Evidence hierarchy
- **E0** Researcher intuition
- **E1** Secondary commentary / industry
- **E2** Scholarly preprint
- **E3** Peer-reviewed research
- **E4** Standards / official specifications / benchmark organizations
- **E5** Independent reproduction / converging empirical evidence
- **E6** Our preregistered reproducible evidence with independent reproduction

Evidence tier describes source strength, not truth. Provenance, authenticity, semantic correctness, temporal validity and independence remain separate questions.

## Claim registry
Every material claim receives: ID, statement, claim type, supporting evidence, contradictory evidence, confidence, status, last reviewed.

States: UNTESTED, SUPPORTED, PARTIALLY_SUPPORTED, CONTESTED, REFUTED, OBSOLETE.

A verified execution outcome is evidence for a research claim; it is not by itself a supported research claim.

## Novelty classification
- N0 Known
- N1 New application
- N2 New combination
- N3 New formalization
- N4 New mechanism
- N5 New empirical result
- N6 New generalizable principle

No N3–N6 claim may advance without literature + patent + source-code + standards + product reconnaissance.

## Hypothesis rule
Every confirmatory study defines:
- research question
- null hypothesis
- alternative hypothesis
- independent/dependent variables
- baselines
- sample size
- exclusion criteria
- metrics
- statistical plan
- success threshold
- falsification conditions

Post-hoc discoveries remain EXPLORATORY.

## ISE-R1 — Grounded verification
When the truth of an asserted outcome is deterministically observable from system state, a subjective, human-preference, or model-generated judgment MUST NOT be the sole basis for VERIFIED.

Prefer, in order when applicable:
1. deterministic state/effect checks;
2. external or domain oracle checks;
3. independent verification bound to the exact subject and evidence;
4. subjective or model judgment as supporting evidence only.

If no deterministic or external oracle exists, the study MUST declare that limitation and justify the evaluation construct. Agreement among judges does not establish construct validity.

Rationale: GAUGE (Bodhwani, Tran & Wei, 2026-09-10, arXiv:2609.12191) reports substantial disagreement between user-simulation satisfaction judgments and grounded task success. This protocol treats that result as external evidence motivating a stricter local rule, not as proof that every judge-based evaluation is invalid.

## ISE-R2 — Adversarial trace evaluation
Long-horizon or stateful claims MUST include applicable falsification cases for:
- stale state or stale facts;
- revocation and revoked-memory reuse;
- contradictory updates/evidence;
- cross-user or cross-tenant isolation;
- constraint decay;
- replay/duplicate effects;
- crash/recovery;
- misleading or adversarial task evidence when the environment can influence agent beliefs.

Each omitted class MUST be marked NOT_APPLICABLE with a reason rather than silently skipped.

Pass/fail should be trace-grounded and deterministic where the claimed property permits it.

Rationale: MemRiskBench (Jiang, Yuan & Li, 2026-09-14, arXiv:2609.14976) operationalizes deterministic trace-grounded checks for several long-horizon memory risks. AgentLSD (Golinelli et al., 2026-09-16, arXiv:2609.19140) motivates testing adversarial task contamination. These are inputs to local falsification design, not imported benchmark claims.

## ISE-R3 — Verified research progress
Activity MUST NOT be reported as scientific progress merely because tokens, attempts, missions, commits, runtime, benchmark executions or judge scores increased.

A research-progress event requires at least one of:
- a Research Protocol progression gate advances on new evidence;
- a registered material claim changes state on new evidence;
- a reproducible failure or counterexample is discovered;
- uncertainty is reduced by a preregistered or explicitly exploratory analysis;
- evidence or verification quality measurably improves.

Where feasible, report progress together with resource denominators:
- tokens;
- wall-clock time;
- financial cost;
- attempts/missions;
- human interventions.

Recommended derived measures include verified_progress_per_cost, replication_success_rate, falsification_yield, deterministic_verification_coverage, independent_verification_coverage, and judge_only_claim_rate. A metric MUST have a declared numerator, denominator, unit, population/window and computation before it is used for a scientific claim.

## Execution/research boundary
The research protocol does not create a new Aftergraph execution plane, verifier, authority source or truth store.

Canonical platform execution remains owned by the platform architecture:
Intent -> Intelligence -> Authority -> Trust -> Runtime -> Execution -> Evidence -> Verification -> Verified Outcome.

Research objects (claims, hypotheses, experiments, replications, falsification analyses) reference execution evidence and verified outcomes. They do not replace WORKS execution truth or Sentinel/domain-verifier verdicts.

## Reproducibility target
A result should aim toward: git clone ... && make reproduce

Record: source commit, environment, dependencies, model/provider/version, parameters, prompts/config, seeds, hardware, dataset/version, raw results, analysis scripts, figure scripts, date.

For evaluations under ISE-R1/R2 also record: verifier/oracle identity, exact subject identity, evidence/trace references, evaluator version, deterministic-check coverage, adversarial-case coverage, and any judge-only dimensions.

## AI-use policy
AI may assist: literature discovery, query generation, coding, data processing, method brainstorming, statistical implementation, critique and writing.

AI output is not evidence. Sources and substantive claims require independent checking. A model-generated evaluator result is an evaluation observation, not independent scientific evidence merely because a model produced it. Final scientific responsibility remains with Jonas Abde.

## Research opponent
Maintain objections: OBJ-xxxx, objection, evidence, response, status.

The research opponent should actively test:
- problem may not exist,
- contribution already exists,
- mechanism may be unnecessary,
- metric may be biased,
- evaluator may not measure the claimed construct,
- confounders may explain effect,
- result may not generalize,
- cost may overwhelm benefits,
- evidence may be stale, contradictory, contaminated or non-independent.

## Progression gates
- G0 Problem exists
- G1 Prior-art gap
- G2 Formal coherence
- G3 Minimal mechanism works
- G4 Material benefit vs baseline
- G5 Causal/ablation support
- G6 Generalization
- G7 Failure resilience
- G8 Independent reproduction
- G9 External criticism survived

Advance only when evidence advances.

## External evidence introduced in v0.2
- Bodhwani, S., Tran, K., & Wei, J. (2026-09-10). GAUGE: When Not to Trust LLM-as-a-Judge in User-Simulated Evaluation of Task-Oriented Agents. arXiv:2609.12191.
- Jiang, Y., Yuan, Y., & Li, X. (2026-09-14). MemRiskBench: Trace-Aware Risk-Preserving Evaluation for Long-Horizon LLM Agents. arXiv:2609.14976.
- Golinelli et al. (2026-09-16). AgentLSD: Evaluating AI Security Agents Under Adversarial Task Contamination. arXiv:2609.19140.

These sources motivate falsifiable requirements. Their reported results are not promoted into local E5/E6 evidence without independent reproduction.
