# Evolutionary Computation Landscape for JAR-EXP-0015

**Experiment:** JAR-EXP-0015  
**Working algorithm:** VERGE — Verified Evolutionary Routing with Governed Exploration  
**Repository:** Aftergraph/intelligence-systems-research  
**Evidence status:** Literature synthesis / design input only. No Aftergraph empirical claim is created by this document.

## Research question

Can an evolutionary controller improve verified agent-execution policy selection under heterogeneous, failure-prone missions while preserving hard authority constraints and reducing false completion, cost, or human intervention relative to fixed and conventional evolutionary baselines?

## Scientific posture

This document does **not** assume VERGE is better. It defines the historical and contemporary prior-art basis against which the mechanism must be falsified.

Empirical hypotheses cannot be proven true in the mathematical sense. They can be supported, refuted, or remain inconclusive under a frozen protocol. Formal invariants may be proven separately.

## Historical line

### 1960s–1970s — evolutionary optimization foundations

Evolution Strategies (Rechenberg/Schwefel lineage) established mutation-driven population search and self-adaptation for engineering optimization. Evolutionary Programming developed in parallel around adaptive behavior. Holland's 1975 *Adaptation in Natural and Artificial Systems* formalized genetic algorithms and schema-oriented adaptation.

Design lesson for VERGE: population search and inheritable variation are established mechanisms; novelty cannot be claimed for using mutation/selection alone.

### 1990s — robust continuous search and problem-class limits

Storn and Price's Differential Evolution (1997) introduced difference-vector mutation for nonlinear, non-differentiable continuous optimization, emphasizing few control variables and parallelizability.

Wolpert and Macready's No Free Lunch theorems (1997) show that optimizer superiority is necessarily problem-class dependent when averaged over all possible objective functions.

Design consequence: VERGE must be evaluated on a declared mission-policy problem class and may not claim universal optimizer superiority.

### 2001–2002 — self-adaptation and multi-objective selection

Hansen and Ostermeier's CMA-ES line formalized covariance adaptation for difficult non-convex continuous landscapes.

Deb et al.'s NSGA-II (2002) established a practical elitist multi-objective method using non-dominated sorting and diversity preservation.

Design consequence: VERGE should not collapse safety, verified success, cost, latency, and human intervention into one arbitrary scalar if the problem is genuinely multi-objective. Hard authority constraints should remain constraints, not cheap negative rewards.

### 2010s — novelty and quality-diversity

MAP-Elites (Mouret & Clune, 2015) reframed search from finding one champion to illuminating a behavior space with high-performing but qualitatively different elites. Later Quality-Diversity work developed archives, emitters, and alternative containers/selection/mutation schemes.

Design consequence: retaining diverse execution policies can provide recovery options and stepping stones that single-best-policy optimization loses.

### 2017 — evolution strategies at modern distributed scale

OpenAI demonstrated ES as a scalable black-box alternative on reinforcement-learning benchmarks, highlighting implementation simplicity, sparse-reward robustness, and distributed scaling.

Design consequence: black-box policy evaluation and massive parallel evaluation remain viable when gradients are unavailable or undesirable.

### 2024–2026 — theory for QD and LLM-assisted evolutionary search

Qian, Xue, and Wang (IJCAI 2024) provided formal runtime results showing that MAP-Elites can outperform a conventional EA on specific combinatorial problem classes, strengthening the theoretical case that diversity can be instrumentally useful rather than decorative.

Google DeepMind's AlphaEvolve (2025) combines LLM-generated program variation with automated evaluators and evolutionary selection. Contemporary surveys of LLM + evolutionary computation describe three broad uses: LLMs as optimizers, embedded variation/search components, and higher-level algorithm selection/generation.

Design consequence: an LLM may be used as a semantic variation operator, but objective evaluators must determine survival. LLM output is proposal generation, not evidence.

## Mechanisms selected for VERGE

VERGE intentionally composes known mechanisms:

1. **Constrained evolutionary search** — authority/security violations are infeasible, not merely low-fitness.
2. **Pareto selection** — verified outcome quality, cost, latency, recovery, and intervention remain separate objectives.
3. **Quality-Diversity archive** — preserve distinct high-performing policy families.
4. **Adaptive operator selection** — mutation/recombination operators receive credit from offspring performance.
5. **Island populations** — preserve exploration and support distributed evaluation.
6. **Semantic variation** — optional LLM-generated policy edits, always evaluator-gated.
7. **Evidence-gated fitness** — self-reported completion cannot directly score as verified success.

## Proposed novelty boundary

The following are **not** novelty claims:

- population-based evolutionary search;
- genetic operators;
- differential mutation;
- Pareto ranking;
- MAP-Elites / QD archives;
- island models;
- LLM-assisted program mutation;
- adaptive operator selection.

Potential contribution, if empirical and ablation evidence supports it:

> A governed evolutionary controller in which execution-policy candidates are evaluated on verified mission outcomes, hard authority constraints are non-negotiable feasibility gates, evidence classes remain explicit, and diversity is maintained over operational behavior descriptors relevant to long-horizon agent execution.

This is currently an **N2/N3 candidate combination/formalization**, not an N4+ mechanism claim.

## Primary prior art

- John H. Holland, *Adaptation in Natural and Artificial Systems*, 1975 / MIT Press edition.
- Rainer Storn & Kenneth Price, “Differential Evolution – A Simple and Efficient Heuristic for Global Optimization over Continuous Spaces,” *Journal of Global Optimization* 11, 341–359, 1997. DOI: 10.1023/A:1008202821328.
- David H. Wolpert & William G. Macready, “No Free Lunch Theorems for Optimization,” *IEEE Transactions on Evolutionary Computation* 1(1), 67–82, 1997. DOI: 10.1109/4235.585893.
- Nikolaus Hansen & Andreas Ostermeier, “Completely derandomized self-adaptation in evolution strategies,” *Evolutionary Computation* 9(2), 159–195, 2001. DOI: 10.1162/106365601750190398.
- Kalyanmoy Deb et al., “A fast and elitist multiobjective genetic algorithm: NSGA-II,” *IEEE Transactions on Evolutionary Computation* 6(2), 182–197, 2002. DOI: 10.1109/4235.996017.
- Jean-Baptiste Mouret & Jeff Clune, “Illuminating search spaces by mapping elites,” 2015, arXiv:1504.04909.
- Tim Salimans et al., “Evolution Strategies as a Scalable Alternative to Reinforcement Learning,” OpenAI, 2017.
- Chao Qian, Ke Xue, Ren-Jian Wang, “Quality-Diversity Algorithms Can Provably Be Helpful for Optimization,” IJCAI 2024, DOI: 10.24963/ijcai.2024/773.
- Google DeepMind, “AlphaEvolve: A Gemini-powered coding agent for designing advanced algorithms,” 2025.
- Yisong Zhang et al., “A Systematic Survey on Large Language Models for Evolutionary Optimization: From Modeling to Solving,” 2025, arXiv:2509.08269.
- Dikshit Chauhan et al., “Evolutionary Computation and Large Language Models: A Survey of Methods, Synergies, and Applications,” 2025, arXiv:2505.15741.

## Falsification obligations

VERGE must be rejected or demoted if any of the following survive controlled testing:

- gains disappear against stronger baselines such as NSGA-II/MAP-Elites/CMA-ES where applicable;
- benefits are explained by larger evaluation budgets rather than mechanism;
- UAR rises materially relative to fixed governed policy;
- diversity archive improves coverage but worsens verified-outcome efficiency without compensating robustness;
- LLM variation adds cost without measurable search benefit;
- performance is brittle to task-family shift or seed;
- a simpler fixed policy matches the verified outcome frontier.

## Evidence boundary

This file establishes **prior-art and design rationale only**. It contains no Aftergraph experimental result for VERGE and must not be cited as evidence that VERGE improves agent execution.
