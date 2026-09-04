# Capabilities, Registries and Interoperability

## Capability
A capability should be richer than a tool name.

Candidate properties:
- ID / namespace
- provider
- input schema
- output schema
- side effects
- required authority
- data classes
- cost estimate
- latency estimate
- reversibility
- idempotency
- evidence produced
- trust requirements

## Side-effect classes
Possible starting taxonomy:
PURE, READ, WRITE, REVERSIBLE_WRITE, EXTERNAL_EFFECT, DESTRUCTIVE, FINANCIAL, IRREVERSIBLE, SAFETY_CRITICAL.

## Capability resolution
If a mission requires `repository.modify`, providers may include:
- local Git skill
- GitHub MCP server
- native connector
- remote A2A coding agent

Provider selection can consider:
capability fit, authority, trust, privacy, cost, latency, quality and availability.

## Registries
Potential registry families:
- capability registry
- agent registry
- mission/template registry
- extension registry
- conformance registry

Deployment modes:
local → organization → federated → public.

## Interoperability goal
A mission should be portable across at least three independent runtimes without rewriting its semantic intent.

Measure:
- adapter LOC
- changed fields
- semantic deviations
- failed conformance tests
- implementation time
- runtime-specific glue

## Framework adapters
Possible adapters:
OpenAI/Codex, Claude, Gemini/ADK, LangGraph, Semantic Kernel, AutoGen, custom runtimes.

The standard should remain independent of any single framework.
