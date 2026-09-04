# ADR-008: RFC 8693 Token Exchange for Mission-Constraint-to-IAM Binding

**Document ID:** ADR-008
**Status:** PROPOSED (design complete; awaiting external security review — recorded as delegated approval in DEC-030)
**Date:** 2026-09-04
**Author:** CONTINUOUS OVERNIGHT MODE (auto-generated)
**Closes:** Q-004 (open_questions.csv, High priority) at the design level
**Related:** ADR-007 (state consistency), SPEC-001 §3.3 (delegation), TH-03/TH-04/TH-12/TH-13 (threat model), capabilities/dispatcher.py

---

## 1. Context

Q-004 (open_questions.csv): *How can RFC 8693 token exchange securely
bind natural-language mission constraints to IAM policies?*

The current implementation (`capabilities/dispatcher.py`) checks
capability URIs against `delegation.scope.allowed`/`denied` lists at
call time. The delegation token itself is an in-process object —
there is no cryptographic binding between (a) the natural-language
mission objective, (b) the machine-readable constraint set, and
(c) the IAM policy of the delegated principal. TH-03 (Delegation
Forgery) and TH-04 (Attenuation Bypass) are defended structurally
but not cryptographically.

RFC 8693 (OAuth 2.0 Token Exchange) provides the industry-standard
mechanism: a subject token is exchanged for a new token with a
different scope/audience, mediated by an authorization server. The
question is how to map SPEC-001's mission concepts onto this.

## 2. Decision Drivers

1. **Constraint provenance**: the natural-language objective is
   frozen at mission creation; the derived constraints must be
   bound to that exact objective text (hash-chained), so a
   verifier can prove the constraints descend from the objective.
2. **Attenuation must be monotonic and verifiable offline**:
   a subagent's token must carry proof that its scope is a subset
   of its parent's, without calling the authorization server
   (mirrors ADR-007's SS control-plane assumption).
3. **No natural-language in the token**: LLM-parsed constraints
   must be serialized to a deterministic schema (JSON Schema
   2020-12, DEC-004's ≤500-token budget) before token issuance.
4. **Composition over reinvention (DEC-002)**: use RFC 8693
   semantics as-is; do not invent a new token format.
5. **Fail-closed (ADR-007 alignment)**: exchange failure or
   signature mismatch = no token = no capability use.

## 3. Design

### 3.1 Token chain

```
Human Principal
  └─ issues Mission Delegation Token (MDT-0)
       claims: purpose=urn:mission:<id>:v<n>,
               objective_hash=sha256(objective_text),
               constraints_hash=sha256(constraints_json),
               scope.allowed[], scope.denied[],
               depth=0, tau=mission TTL
       signed by: Human Principal key

Worker Agent (depth 1)
  └─ RFC 8693 exchange (actor_token=MDT-0)
       receives MDT-1: scope.allowed ⊆ MDT-0.scope.allowed,
                       depth=1, tau ≤ MDT-0.tau
       signed by: Authorization Server (the Control Plane)
```

Each sub-delegation is one RFC 8693 exchange. The exchanged token
is a standard JWT with SPEC-001 extension claims (below).

### 3.2 Extension claims (SPEC-001 delegation profile)

| Claim | Type | Meaning |
|---|---|---|
| `purpose` | URN | `urn:mission:<mission_id>:v<version>` — TH-03 binding |
| `objective_hash` | hex | sha256 of frozen NL objective text |
| `constraints_hash` | hex | sha256 of serialized constraint set (deterministic JSON, sorted keys) |
| `scope.allowed` | URI[] | capability URIs granted (attenuated) |
| `scope.denied` | URI[] | capability URIs explicitly forbidden |
| `depth` | int | delegation depth (monotonic, for TH-04) |
| `tau` | timestamp | token expiry ≤ parent tau |
| `parent_hash` | hex | sha256 of parent token (hash chain for audit) |
| `amr` | string[] | attestation method: which verifier class derived the constraints |

### 3.3 Constraint derivation flow

1. Mission created with NL objective `O`.
2. Control plane serializes constraints `C` (deterministic JSON,
   sorted keys, no whitespace) and computes `constraints_hash`.
3. Both hashes are embedded in MDT-0 at issuance.
4. At any later point, a verifier recomputes both hashes from the
   on-disk mission object. **Mismatch = the mission was mutated
   post-issuance = fail-closed** (TH-12 TOCTOU window closes:
   the token binds the exact constraint text that was checked).

### 3.4 IAM policy mapping

The Control Plane maintains a mapping:

```
capability URI prefix  →  IAM action template
mcp://github/repo:read →  GitHubRepoRead( repo=<from token context> )
mcp://aws/s3:put       →  s3:PutObject restricted by condition
                          aws:ResourceTag/mission == <mission_id>
```

IAM policies generated from MDT are **always condition-restricted**:
every generated policy statement carries a condition binding the
session to `purpose`. Revocation = marking the mission's
`delegation_id` inactive in the Control Plane; cached IAM sessions
expire at `tau` (bounded by the shortest-lived MDT in the chain).

### 3.5 What this design deliberately does NOT do

- **No NL text inside tokens.** Only hashes travel; the text
  lives in the mission object (decoupled per TH-07).
- **No LLM in the trust path.** The LLM that parses the objective
  is a *hint generator*; the Control Plane's deterministic
  serializer is the authority. A hostile or hallucinating LLM
  cannot widen scope (it can only propose; issuance filters).
- **No cross-org token trust.** Tokens are only valid within one
  Control Plane instance; federated scenarios are out of scope
  (recorded as a Q-004 follow-up).

## 4. Consequences

### Positive
- TH-03 (forgery) is cryptographically closed: tokens are signed
  by the Control Plane, purpose-bound, hash-chained.
- TH-04 (amplification) is mechanically verified at every exchange
  (scope subset check is a set operation, not a policy judgment).
- TH-12 (TOCTOU) closes: the constraint hash binds the checked
  text to the used token.
- Offline verification (hash chain + signature) matches ADR-007's
  SS control-plane model; no consensus call in the capability hot path.

### Negative / ceilings (ponytail:)
- The authorization server (Control Plane) is a single point of
  failure for *issuance* (not for *verification*). Mitigation:
  fail-closed + standard HA deployment patterns.
- `objective_hash` assumes the NL objective is stable; any
  re-wording invalidates all delegated tokens (this is intended,
  but operators must know).
- Revocation latency is bounded by `tau`, not instant, unless
  CapabilityDispatcher checks Control Plane liveness per call
  (an explicit trade-off; current dispatcher checks per call, so
  revocation IS instant in-process — the ceiling only applies to
  IAM-side sessions).

## 5. Implementation plan

| Phase | Action | Gate |
|---|---|---|
| 7 | Add `delegation/token_exchange.py` with issue/exchange/verify functions (pure, stdlib+jwt) | Unit tests, no network |
| 7 | Add `tests/test_token_exchange_q004.py` (≥10 tests: issue, exchange, attenuation subset check, hash mismatch, expired, forged signature, depth overflow, purpose mismatch, deny-list precedence, tau monotonicity) | All pass |
| 8 | Wire into `capabilities/dispatcher.py`: verify token before every capability call | Existing dispatcher tests still pass |
| 9 | Chaos: verify behavior when signature check fails mid-mission | Fail-closed asserted |
| 10 | Phase 2 LIVE validation with real IAM side-effects | Q-011-gated |

## 6. Reviewer checklist

- [ ] Is the constraints_hash canonicalization specified tightly
      enough (sorted keys, no whitespace, UTF-8) to be reproducible
      across languages?
- [ ] Does every generated IAM statement carry the purpose condition?
- [ ] Is the depth counter incremented at every exchange and capped?
- [ ] Is the fail-closed path tested for each failure class?
- [ ] Is any SIMULATED evidence at risk of is_live upgrade through
      this path? (No: token exchange never touches ProviderResponse.)

## 7. References

- RFC 8693 (OAuth 2.0 Token Exchange)
- DEC-002 (compose over reinvent), DEC-004 (schema budget)
- ADR-007 (state consistency — SS control plane)
- TH-03, TH-04, TH-12, TH-13 in security/THREAT-MODEL-AND-SUPPLY-CHAIN.md
- capabilities/dispatcher.py (current enforcement point)
- Q-005 hardening (DEC-023) — principal identity semantics reused here
