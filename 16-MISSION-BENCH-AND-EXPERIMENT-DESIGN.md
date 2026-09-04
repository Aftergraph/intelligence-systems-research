# MISSION-Bench and Experiment Design

## Core experiment
Same workload, same base model/tools where possible.

### BEFORE
User → agent → tools → declared done.

### AFTER
User → mission → authority/state/capabilities → execution → assurance → evidence → verified outcome.

## Ablation ladder
1. Baseline agent
2. + Mission Contract
3. + Persistent State
4. + Authority
5. + Verification
6. + Evidence
7. + Recovery
8. + Cost-aware capability routing
9. Full system

This isolates causal contributions.

## Model matrix
At least:
- frontier model(s)
- mid-tier model(s)
- small/open/local model(s)

Test whether spec complexity harms smaller models.

## Runtime matrix
At least three independent implementations/frameworks.

Goal:
same mission semantics, different runtimes.

## Metric vector
Do not use one leaderboard score.

Suggested vector:
[VSR, FCR, CRR, CPVO, TVO, UnauthorizedRate, RecoveryRate, HumanMinutes, Memory, Energy]

## Failure injection
- API unavailable
- tool timeout
- bad tool output
- stale state
- contradictory evidence
- authority revoked
- context loss
- budget exhausted
- verifier unavailable
- partial execution
- environment/UI/filesystem changes
- model failure

## Statistical requirements
- confidence intervals
- effect sizes
- variance
- power/sample-size rationale where practical
- preregistration for confirmatory claims
- separate exploratory analysis

## Benchmark validity
Every benchmark profile should start with a decision:
“What real system choice is this benchmark intended to support?”

## Anti-cheating / future benchmark needs
- private/held-out tasks
- versioned environments
- sealed test sets where needed
- baseline disclosure
- model/runtime/config disclosure
