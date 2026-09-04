# Schema Design Notes

Candidate normative object schemas:
- IntelligenceSystem
- Mission
- Principal
- Delegation
- Capability
- AuthorityGrant
- StateSnapshot
- TrajectoryEvent
- AssurancePlan
- Evidence
- VerificationResult
- RuntimeProfile
- ExtensionManifest

Working direction:
- human-friendly YAML authoring may be allowed;
- canonical JSON representation should be investigated for deterministic hashing/signing;
- JSON Schema 2020-12 is a strong compatibility candidate;
- schema versioning and extension namespaces must be explicit.

No schema in this package is yet normative.
