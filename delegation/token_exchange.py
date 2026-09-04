"""
delegation/token_exchange.py
============================

ADR-008 Phase 7 implementation: RFC 8693-style token exchange for
SPEC-001 mission delegation. Pure stdlib + PyJWT; no network calls.

Implements:
- canonical_constraints_hash: deterministic JSON canonicalization
  for the constraints_hash claim (sorted keys, no whitespace, UTF-8).
- issue_mission_token (MDT-0): Human Principal -> mission token with
  objective_hash + constraints_hash + scope + purpose.
- exchange_token (MDT-n -> MDT-n+1): RFC 8693-style exchange with
  monotonic attenuation (scope subset, depth increment, tau shrink).
- verify_token: fail-closed verification (signature, expiry, depth,
  purpose, attenuation against parent).

ponytail: HS256 with a symmetric key is enough for the single
Control Plane instance (this program's scope). Asymmetric RS/ES
signing is the upgrade path for multi-party verification; the
module is written so the algorithm is a parameter.
"""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

import jwt as pyjwt

# ponytail: secret is injected by the caller (env-var per program rules).
# A module-level default is a placeholder for tests only.
DEFAULT_SIGNING_SECRET = "adr008-test-only-secret"


class TokenExchangeError(Exception):
    """Fail-closed: any verification or exchange failure."""


def canonical_constraints_hash(constraints: Dict[str, Any]) -> str:
    """Deterministic hash of the constraint set.

    Canonicalization (ADR-008 §3.3): sorted keys, separators without
    whitespace, ensure_ascii=False, UTF-8 encode, sha256.
    """
    canonical = json.dumps(
        constraints, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def objective_hash(objective_text: str) -> str:
    """sha256 of the frozen natural-language objective text."""
    return hashlib.sha256(objective_text.encode("utf-8")).hexdigest()


def _now() -> int:
    return int(time.time())


def issue_mission_token(
    mission_id: str,
    mission_version: int,
    objective_text: str,
    constraints: Dict[str, Any],
    scope_allowed: List[str],
    scope_denied: Optional[List[str]] = None,
    tau: Optional[int] = None,
    principal: str = "urn:principal:human:owner",
    secret: str = DEFAULT_SIGNING_SECRET,
    depth: int = 0,
) -> str:
    """Issues MDT-0: the Mission Delegation Token from the Human Principal.

    This is the root of the delegation chain (not itself an RFC 8693
    exchange — it is a fresh issuance signed by the principal).
    """
    if not mission_id:
        raise TokenExchangeError("mission_id is required")
    if not scope_allowed:
        # fail-closed: an empty scope grants nothing and is a config error
        raise TokenExchangeError("scope_allowed must be non-empty")
    now = _now()
    claims = {
        "purpose": f"urn:mission:{mission_id}:v{mission_version}",
        "objective_hash": objective_hash(objective_text),
        "constraints_hash": canonical_constraints_hash(constraints),
        "scope": {"allowed": sorted(scope_allowed),
                  "denied": sorted(scope_denied or [])},
        "depth": depth,
        "iss": principal,
        "sub": principal,
        "iat": now,
        "exp": tau if tau is not None else now + 3600,
        "amr": ["mission_control_plane"],
    }
    return pyjwt.encode(claims, secret, algorithm="HS256")


def exchange_token(
    parent_token: str,
    requested_scope_allowed: List[str],
    requested_scope_denied: Optional[List[str]] = None,
    tau: Optional[int] = None,
    actor: str = "urn:principal:agent:worker",
    secret: str = DEFAULT_SIGNING_SECRET,
    max_depth: int = 8,
) -> str:
    """RFC 8693-style exchange: parent MDT -> child MDT.

    Attenuation invariants (fail-closed, TH-04/TH-13):
      - child.scope.allowed ⊆ parent.scope.allowed
      - child.scope.denied ⊇ parent.scope.denied
      - child.depth = parent.depth + 1 ≤ max_depth
      - child.tau ≤ parent.tau
      - parent_hash chains to the parent for the audit trail.
    """
    try:
        parent = pyjwt.decode(parent_token, secret, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError as e:
        raise TokenExchangeError(f"parent token expired: {e}") from e
    except pyjwt.InvalidTokenError as e:
        raise TokenExchangeError(f"parent token invalid: {e}") from e

    parent_allowed = set(parent.get("scope", {}).get("allowed", []))
    parent_denied = set(parent.get("scope", {}).get("denied", []))
    parent_depth = int(parent.get("depth", 0))
    parent_exp = int(parent.get("exp", 0))

    req_allowed = set(requested_scope_allowed)
    req_denied = set(requested_scope_denied or [])

    # Monotonic attenuation: subset check (TH-04)
    if not req_allowed.issubset(parent_allowed):
        widened = req_allowed - parent_allowed
        raise TokenExchangeError(
            f"attenuation violation: requested capabilities not in parent scope: "
            f"{sorted(widened)}"
        )

    child_depth = parent_depth + 1
    if child_depth > max_depth:
        raise TokenExchangeError(
            f"delegation depth {child_depth} exceeds max_depth {max_depth}"
        )

    # tau monotonicity: child expiry cannot exceed parent expiry
    child_exp = tau if tau is not None else parent_exp
    if child_exp > parent_exp:
        raise TokenExchangeError(
            f"tau violation: child expiry {child_exp} exceeds parent expiry {parent_exp}"
        )

    # denied list must only grow (intersection over parent's denied ∪ requested)
    child_denied = parent_denied | req_denied

    now = _now()
    claims = {
        "purpose": parent["purpose"],
        "objective_hash": parent["objective_hash"],
        "constraints_hash": parent["constraints_hash"],
        "scope": {"allowed": sorted(req_allowed), "denied": sorted(child_denied)},
        "depth": child_depth,
        "iss": parent["iss"],           # original issuer stays for audit
        "sub": actor,                   # the actor this token authorizes
        "act": {"sub": actor},          # RFC 8693 actor claim
        "iat": now,
        "exp": child_exp,
        "parent_hash": hashlib.sha256(parent_token.encode("utf-8")).hexdigest(),
        "amr": parent.get("amr", []) + ["token_exchange"],
    }
    return pyjwt.encode(claims, secret, algorithm="HS256")


def verify_token(
    token: str,
    secret: str = DEFAULT_SIGNING_SECRET,
    mission_id: Optional[str] = None,
    require_capability: Optional[str] = None,
    constraints: Optional[Dict[str, Any]] = None,
    objective_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Fail-closed verification. Returns claims or raises TokenExchangeError.

    When `constraints` (and/or `objective_text`) is provided, the stored
    hash is recomputed and compared — a mismatch means the mission object
    was mutated post-issuance (TH-12 TOCTOU closure).
    """
    try:
        claims = pyjwt.decode(token, secret, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError as e:
        raise TokenExchangeError(f"token expired: {e}") from e
    except pyjwt.InvalidTokenError as e:
        raise TokenExchangeError(f"token invalid: {e}") from e

    if mission_id is not None:
        expected_purpose = f"urn:mission:{mission_id}:"
        if not claims.get("purpose", "").startswith(expected_purpose):
            raise TokenExchangeError(
                f"purpose mismatch: {claims.get('purpose')!r} does not bind "
                f"to mission {mission_id!r}"
            )

    if require_capability is not None:
        allowed = set(claims.get("scope", {}).get("allowed", []))
        denied = set(claims.get("scope", {}).get("denied", []))
        if require_capability in denied:
            raise TokenExchangeError(
                f"capability {require_capability!r} is explicitly denied"
            )
        if require_capability not in allowed:
            raise TokenExchangeError(
                f"capability {require_capability!r} is not in allowed scope"
            )

    if constraints is not None:
        stored = claims.get("constraints_hash")
        recomputed = canonical_constraints_hash(constraints)
        if stored != recomputed:
            raise TokenExchangeError(
                "constraints_hash mismatch: mission constraints were mutated "
                "after token issuance (TOCTOU / post-issuance modification)"
            )

    if objective_text is not None:
        stored = claims.get("objective_hash")
        recomputed = objective_hash(objective_text)
        if stored != recomputed:
            raise TokenExchangeError(
                "objective_hash mismatch: mission objective was mutated "
                "after token issuance"
            )

    return claims
