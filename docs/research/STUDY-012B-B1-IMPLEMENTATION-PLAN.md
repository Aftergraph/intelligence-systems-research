# STUDY-012B B1 implementation plan

1. Verify the committed B1 tests fail for the intended missing implementation.
2. Implement deterministic pair planning across repository, ledger, and agentops fixtures.
3. Recreate a fresh disposable fixture for every condition execution.
4. Bind pair identity to study, replicate, seed, fixture kind, and scenario id.
5. Randomize I0/I3 order deterministically per pair while preserving identical actor intent.
6. Preserve HARNESS_VALIDATION_ONLY and confirmatory_eligible=false.
7. Run full CI, audit, CodeQL, and reproducibility checks before marking B1 green.
