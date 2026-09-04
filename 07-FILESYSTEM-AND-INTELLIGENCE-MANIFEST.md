# Filesystem and Intelligence Manifest

## Hypothesis
AI-native systems may benefit from a predictable filesystem entry point, but the filename and schema are not yet fixed.

Working placeholder:
`INTELLIGENCE.yaml`

## Candidate layout
project/
├── README.md
├── AGENTS.md
├── INTELLIGENCE.yaml
├── .agents/
│   └── skills/
├── .intelligence/
│   ├── missions/
│   ├── capabilities/
│   ├── agents/
│   ├── models/
│   ├── policies/
│   ├── authority/
│   ├── assurance/
│   ├── evals/
│   ├── schemas/
│   ├── extensions/
│   └── compliance/
└── src/

Runtime state should normally live separately and not be committed:
.runtime/
└── mission-id/
    └── run-id/
        ├── state/
        ├── trajectory/
        ├── evidence/
        ├── telemetry/
        └── artifacts/

## Root manifest responsibilities
- identify system/spec version
- import instructions
- discover skills
- reference MCP/A2A endpoints/providers
- locate missions/policies/assurance
- declare organization/project metadata
- expose extension points
- define precedence/import behavior

## Critical unresolved rules
- exact filename
- YAML vs JSON authoring
- canonical signable form
- monorepos
- nested manifests
- inheritance
- precedence
- organization overrides
- remote discovery
- `.well-known` discovery
- extension conflict rules

## Machine-first / human-first split
YAML may be convenient for authors.
Canonical JSON may be preferable for deterministic hashing/signing.
This is a hypothesis to test, not a fixed decision.

## Complexity budget
Core specification should have an explicit size budget:
- minimal required concepts
- minimal required fields
- minimal token footprint when shown to an LLM
- extension-based progressive disclosure
