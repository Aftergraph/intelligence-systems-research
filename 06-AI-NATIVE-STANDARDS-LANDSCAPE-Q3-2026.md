# AI-Native Standards Landscape — Q3 2026

## Principle
The project should compose existing standards instead of reimplementing them for branding.

## Existing layers to map

### Repo/project instructions
**AGENTS.md**
Working interpretation: local human-readable instructions for coding agents and repository behavior.

### Portable procedures
**Agent Skills / SKILL.md**
Reusable, filesystem-native instructions plus scripts/references/assets.

### Tools and data
**Model Context Protocol (MCP)**
Protocol for model/tool/resource interaction. Do not assume a single universal `mcp.json` file is the protocol standard.

### Agent-to-agent interoperability
**A2A**
Agent discovery and communication; Agent Card is an important discovery primitive.

### Identity / workload
OAuth/OIDC and workload-identity patterns such as SPIFFE should be mapped rather than replaced.

### Runtime controls
OWASP agent-control and agentic-security work should inform runtime-policy hooks.

### Observability
OpenTelemetry GenAI semantic conventions should be used where possible for telemetry mapping.

### Assurance
NIST TEVV concepts provide external framing for Test/Evaluation/Verification/Validation.

### Supply chain
CycloneDX ML-BOM and related provenance approaches can represent models, datasets and software/AI dependencies.

### Content provenance
C2PA-style signed provenance can be an evidence provider where relevant.

### Governance
ISO/IEC 42001, impact-assessment standards, NIST AI RMF and sector/legal profiles may serve as governance mappings.

## Potential unresolved layer
Preliminary hypothesis only:

A vendor-neutral contract for:
intent → mission → state → capability composition → delegated authority → resource constraints → execution → assurance → evidence → verified outcome.

This must be proven as a gap, not assumed.
