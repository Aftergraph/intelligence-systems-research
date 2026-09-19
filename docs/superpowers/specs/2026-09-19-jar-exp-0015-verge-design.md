# JAR-EXP-0015 — VERGE Design

**VERGE:** Verified Evolutionary Routing with Governed Exploration  
**Status:** DESIGN — research only; no empirical or production claim.  
**Canonical owner:** Aftergraph/intelligence-systems-research.

## Purpose

VERGE is a research-only evolutionary controller for discovering agent-execution policies that improve **verified** mission outcomes under heterogeneous tasks, failures, costs, and bounded authority.

Research loop:

```text
candidate policy
→ controlled mission
→ evidence
→ independent verifier
→ objective vector
→ constrained selection
→ variation
→ next generation
```

VERGE does not replace AIE, Trust Gateway, Runtime, WORKS, Sentinel, ACC, or any production control plane.

## Hypotheses

**H0:** Under equal evaluation budgets, VERGE provides no reproducible improvement over fixed governed policies or the strongest eligible evolutionary baseline.

**H1:** Under equal budgets on the preregistered mission-policy problem class, VERGE improves at least one primary verified-outcome objective without degrading the frozen safety constraints.

**H2:** Quality-Diversity preservation improves robustness to task-family/failure-mode shift versus a Pareto-only ablation.

**H3:** Adaptive operator selection improves sample efficiency versus fixed operator probabilities.

**H4:** LLM semantic mutation is retained only if it improves cost-normalized search performance versus non-LLM variation.

## Hard constraints

- unauthorized action is a feasibility failure, not a soft fitness penalty;
- evidence fabrication or verifier bypass invalidates a candidate;
- evolutionary operators cannot widen the external evaluation mandate;
- candidate policies cannot modify verifier logic, benchmark cases, acceptance criteria, or frozen statistics;
- self-reported completion never equals verified completion;
- research candidates cannot mutate production systems.

## Policy genome

```text
PolicyGenome
├── routing genes
├── blocker/continuation genes
├── topology genes
├── numeric thresholds
├── verification genes
└── meta-genes for operator probabilities
```

Authority is external to the genome.

## Objectives

Primary multi-objective vector:

```text
maximize: VSR, RecoveryRate
minimize: FCR, UAR, CPVO, TVO, HumanInterventionRate
```

Behavioral diversity is tracked separately through the QD archive. UAR and evidence-integrity failures are hard feasibility gates.

Secondary diagnostics: hypervolume, archive coverage, QD score, operator entropy, stagnation, context/token usage, tool calls, and variance across seeds.

## Selection

Three stages:

1. feasibility filter;
2. Pareto ranking;
3. diversity preservation.

The first implementation may use NSGA-II-style nondominated sorting/crowding for stage 2 while preserving an independent MAP-Elites-style archive.

## Quality-Diversity archive

Initial behavior descriptors:

- parallelism intensity;
- intervention dependence;
- cost profile;
- recovery style;
- tool diversity;
- context footprint;
- verification depth;
- latency profile.

The archive stores high-performing **feasible** policies plus exact provenance.

## Variation operators

Initial pool:

- NumericPerturbation
- RuleMutation
- GraphMutation
- PolicyCrossover
- DifferentialMutation
- ArchiveRecombination
- SemanticLLMMutation

Every mutation emits a receipt with parent hashes, operator ID, seed, changed fields, and candidate hash.

LLM variation proposes candidates only. It does not score or verify them.

## Adaptive operator selection

Each operator receives online credit from evaluator-backed offspring improvement. The initial mechanism should use bounded probability matching or a bandit-style controller, then be ablated against fixed probabilities.

## Island populations

Initial search biases:

- conservative;
- exploratory;
- low-cost;
- recovery-heavy.

Migration occurs at frozen intervals and preserves lineage.

## Evidence-gated evaluation

Each evaluation records:

```text
candidate_hash
benchmark_case
seed
environment
mission_result
verifier_result
evidence_refs
objective_vector
feasibility_verdict
cost
latency
```

Fitness can use only admitted evaluator evidence.

## Formal invariants

**I1 Authority non-expansion**

```text
EffectiveAuthority(child) ⊆ EvaluationMandate
```

**I2 Evidence-gated success**

```text
VerifiedSuccess(x) => VerifierPass(x) AND EvidenceAdmitted(x)
```

**I3 No self-attested settlement**

```text
SelfAssertion(x) AND NOT VerifierPass(x) => NOT VerifiedSuccess(x)
```

**I4 Frozen benchmark semantics**

Candidates cannot change workloads, acceptance criteria, verifier code, objectives, exclusions, or statistical thresholds within a frozen run.

**I5 Exact lineage**

Every candidate is reconstructable from parents, operator receipt, seed, algorithm version, and benchmark version.

## Mandatory baselines

- B0 random search
- B1 fixed governed policy
- B2 simple Genetic Algorithm
- B3 Differential Evolution on numeric subspace
- B4 CMA-ES on numeric subspace
- B5 NSGA-II
- B6 MAP-Elites
- B7 LLM-only iterative rewrite
- B8 VERGE without adaptive operators
- B9 VERGE without QD archive
- B10 VERGE without LLM mutation
- B11 full VERGE

Equal evaluation budgets are required wherever representations permit.

## Evaluation layers

**Layer 1 — classical optimization:** Sphere, Rosenbrock, Rastrigin, Ackley. Validates mechanics only.

**Layer 2 — controlled agent simulation:** stale state, tool timeout, malformed result, dependency blocker, context loss, revocation, verifier failure, parallel conflict, false-completion temptation, provider unavailability.

**Layer 3 — controlled real-agent missions:** only after deterministic harness closure and explicit run authorization.

## Statistical requirements

- paired task sets;
- frozen budgets and software/model versions;
- at least 30 independent seeds per deterministic cell unless power analysis says otherwise;
- effect sizes + confidence intervals;
- appropriate paired tests;
- correction for confirmatory multiple comparisons;
- retain failed/negative runs;
- no favorable-result stopping.

## Falsification

VERGE is supported only if its preregistered verified-outcome frontier improves against the strongest eligible baseline, the safety bound is maintained, the effect survives cost normalization and task/seed robustness checks, and ablations show nontrivial contribution from at least one proposed mechanism.

It is refuted or demoted if a simpler baseline matches/exceeds it under equal budget, safety degrades, gains disappear after cost/evaluation normalization, or complexity adds no reproducible benefit.

## Promotion boundary

Positive results remain research evidence. Production promotion requires independent review, canonical-owner mapping, governed implementation, and exact-state verification.
