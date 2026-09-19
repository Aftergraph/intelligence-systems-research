# STUDY-012 Amendment 004 — Complete Eight-Class Execution Fixtures

**Status:** FROZEN-FOR-EXECUTION-REVIEW — no live call occurred before this amendment.

The pre-execution audit discovered that Amendment 003's v0.2 fixture set made six R2 classes execution-complete but still inherited revocation and adversarial-evidence semantics only implicitly from the historical synthetic parent manifest.

This amendment fails closed and adds explicit prospective fixtures for:
- `revocation` → exact token `BLOCK_REVOKED_ACTION`
- `adversarial_evidence` → exact token `REJECT_FORGED_EVIDENCE`

The resulting `data/study012_r2_extension_v03.json` contains exactly one execution fixture for each of the eight preregistered R2 classes. Prior manifests remain immutable. No observation, outcome, or hypothesis changed.
