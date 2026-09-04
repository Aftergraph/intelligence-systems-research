# Assurance, Verification and Evidence

## Assurance is broader than verification
Use four explicit concepts:
- Test
- Evaluation
- Verification
- Validation

## Key distinction
Schema-valid output is not equivalent to semantically correct output.

Therefore measure separately:
- Schema Compliance
- Semantic Compliance
- Outcome Correctness

## Evidence model
Evidence should bind to claims.

claim → evidence → verifier → result

Possible evidence classes:
- self assertion
- model-derived judgment
- deterministic test
- provider receipt
- independent observation
- human approval
- cryptographic attestation
- hardware attestation

Evidence classes must not be assumed equally strong.

## Freshness
Evidence requires:
observed_at, valid_from, valid_until/freshness rule, environment/version binding.

## Verification independence
Open research question:
What level of separation qualifies as independent?
- same model / different prompt
- separate agent
- separate model
- separate provider
- deterministic verifier
- external service
- human verifier

This should be experimentally tested.

## Completion states
Do not collapse:
EXECUTION_COMPLETE
and
OUTCOME_VERIFIED.

Potential lifecycle:
DRAFT → READY → AUTHORIZED → RUNNING → VERIFYING → VERIFIED
with BLOCKED, PAUSED, NEEDS_INPUT, FAILED, CANCELLED, REVOKED, ROLLED_BACK, PARTIAL.
