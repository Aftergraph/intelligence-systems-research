# Identity, Authority and Delegation

## Principal model
Potential principal types:
- human
- agent
- service
- workload
- organization
- device

## Delegation must answer
- who delegates?
- to whom?
- which capabilities?
- for what purpose?
- under which constraints?
- until when?
- may it be re-delegated?
- how is it revoked?
- what proof binds the delegation?

## Candidate object
delegation:
  principal: human:jonas
  delegate: agent:release-agent
  purpose: mission:release-4.8
  capabilities:
    - repository.modify
  constraints:
    branch: release/4.8
  expires_at: ...
  redelegation: false

## Required semantics
- attenuation
- expiry
- revocation
- replay protection
- confused-deputy protection
- delegation chain reconstruction
- policy decisions
- non-repudiation where required

## Relationship to AIE
AIE is the primary research track for institutional legitimacy, delegation, budget and revocation semantics.
The broader system contract should reference or map such semantics instead of pretending they were invented twice.
