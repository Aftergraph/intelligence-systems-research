# Metrics, Cost, Performance and Economics

## Principle
A more controlled system is not automatically a better system.
Every additional control, verifier, policy check and context object has cost.

## Outcome metrics
- Task Success Rate (TSR)
- Verified Success Rate (VSR)
- False Completion Rate (FCR)
- Constraint Retention Rate (CRR)
- Recovery Rate
- Unauthorized Action Rate
- Evidence Completeness

## Time metrics
- Time to First Value
- Time to Verified Outcome (TVO)
- turn latency
- tool latency
- verification latency
- queue/wait latency
- human wait latency
- p50/p90/p99

## Economic metrics
Mission Cost =
model input/output + tools + compute + storage + verification + human cost.

Important:
- Cost Per Success
- Cost Per Verified Outcome (CPVO)
- Cost attribution by mission/submission/provider
- predicted vs actual cost
- budget utilization

## Control-plane tax
Measure cost attributable to:
policy, state, orchestration, capability resolution, verification, telemetry and evidence.

ControlPlaneTax = control overhead / total execution cost

Measure in:
tokens, money, latency, CPU/GPU time, memory and network.

## Context pressure
Measure:
- system-contract tokens
- tool-schema tokens
- mission tokens
- state tokens
- trajectory tokens
- evidence tokens
- actual task tokens

Candidate:
Useful Context Ratio = task-relevant tokens / total context tokens

## Compute and resource metrics
- CPU seconds
- GPU seconds
- NPU seconds
- peak/average memory
- storage per mission
- network bytes
- energy / Wh where measurable
- compute per verified outcome

## Agent efficiency
- useful action rate
- redundant tool calls
- duplicate inference
- retries
- recovery success per retry
- cache hit rate

## Human-effort metrics
- human minutes per verified outcome
- interventions per mission
- approvals per mission
- takeover frequency
- takeover latency

## Portability and integration metrics
- adapter LOC
- implementation hours
- custom glue removed
- semantic deviations
- framework-specific fields
- conformance failures

## Model comprehension
Test whether models correctly extract:
objective, constraints, permissions, capability requirements and completion criteria from the contract.

Metric:
Contract Understanding Accuracy.

## Standard complexity
Measure:
- required concepts
- mandatory fields
- minimal serialized size
- token footprint
- authoring time
- configuration error rate
- developer comprehension

## Decision profiles
Do not collapse everything into one score.
Example profiles:
Enterprise Safety, Consumer, Robotics, Research, Edge/Offline.

Report the Pareto frontier between reliability, latency, cost and human effort.
