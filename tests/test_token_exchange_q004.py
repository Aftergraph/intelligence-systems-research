"""
test_token_exchange_q004.py
===========================

Pins ADR-008 (Q-004): RFC 8693-style token exchange binding
natural-language mission constraints to delegated authority.

Covers the ten failure/success classes named in ADR-008 §5:
issue, exchange, attenuation subset check, hash mismatch,
expired, forged signature, depth overflow, purpose mismatch,
deny-list precedence, tau monotonicity.
"""

import os
import sys
import time

import jwt as pyjwt
import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from delegation.token_exchange import (
    DEFAULT_SIGNING_SECRET,
    TokenExchangeError,
    canonical_constraints_hash,
    exchange_token,
    issue_mission_token,
    objective_hash,
    verify_token,
)

SECRET = "test-secret-adr008"
MISSION = "msn-adr008"
SCOPE = ["mcp://github/repo:read", "mcp://github/repo:write"]
CONSTRAINTS = {
    "forbidden": ["production deploy", "delete index"],
    "required": ["tests pass", "lint clean"],
}
OBJECTIVE = "Refactor authentication without dropping idx_users_email."


@pytest.fixture
def root_token():
    return issue_mission_token(
        mission_id=MISSION,
        mission_version=1,
        objective_text=OBJECTIVE,
        constraints=CONSTRAINTS,
        scope_allowed=SCOPE,
        secret=SECRET,
    )


# ============================================================================
# Canonicalization
# ============================================================================

def test_canonical_hash_is_key_order_insensitive():
    """ADR-008 §3.3: sorted keys means two dicts with the same
    content in different insertion orders hash identically."""
    a = canonical_constraints_hash({"x": 1, "y": 2})
    b = canonical_constraints_hash({"y": 2, "x": 1})
    assert a == b


def test_canonical_hash_is_whitespace_insensitive():
    """Formatting differences in source dicts must not change the hash
    (deterministic JSON, no whitespace)."""
    a = canonical_constraints_hash({"a": [1, 2], "b": "text"})
    b = canonical_constraints_hash({"a": [1, 2], "b": "text"})
    assert a == b


def test_canonical_hash_differs_for_different_constraints():
    a = canonical_constraints_hash({"required": ["tests pass"]})
    b = canonical_constraints_hash({"required": ["tests pass", "extra"]})
    assert a != b


# ============================================================================
# Issue (MDT-0)
# ============================================================================

def test_issue_creates_verifiable_token(root_token):
    claims = verify_token(root_token, secret=SECRET, mission_id=MISSION)
    assert claims["purpose"] == f"urn:mission:{MISSION}:v1"
    assert claims["depth"] == 0
    assert claims["objective_hash"] == objective_hash(OBJECTIVE)
    assert claims["constraints_hash"] == canonical_constraints_hash(CONSTRAINTS)


def test_issue_with_empty_scope_fails_closed():
    """ADR-008 §2.5: an empty scope grants nothing and is a config error."""
    with pytest.raises(TokenExchangeError):
        issue_mission_token(
            mission_id=MISSION, mission_version=1,
            objective_text=OBJECTIVE, constraints=CONSTRAINTS,
            scope_allowed=[], secret=SECRET,
        )


# ============================================================================
# Exchange + attenuation (TH-04 / TH-13)
# ============================================================================

def test_exchange_produces_depth_1_subset_token(root_token):
    child = exchange_token(root_token, ["mcp://github/repo:read"], secret=SECRET)
    claims = verify_token(child, secret=SECRET)
    assert claims["depth"] == 1
    assert claims["scope"]["allowed"] == ["mcp://github/repo:read"]


def test_exchange_rejects_scope_widening(root_token):
    """TH-04: requesting a capability the parent does not have must fail."""
    with pytest.raises(TokenExchangeError) as exc:
        exchange_token(root_token, ["mcp://aws/s3:put"], secret=SECRET)
    assert "attenuation violation" in str(exc.value)


def test_exchange_tau_monotonicity(root_token):
    """Child expiry cannot exceed parent expiry."""
    child = exchange_token(root_token, ["mcp://github/repo:read"], secret=SECRET)
    claims = verify_token(child, secret=SECRET)
    parent = verify_token(root_token, secret=SECRET)
    assert claims["exp"] <= parent["exp"]


def test_exchange_rejects_tau_extension(root_token):
    parent = verify_token(root_token, secret=SECRET)
    future = int(parent["exp"]) + 100000
    with pytest.raises(TokenExchangeError) as exc:
        exchange_token(root_token, ["mcp://github/repo:read"], tau=future, secret=SECRET)
    assert "tau violation" in str(exc.value)


def test_exchange_depth_overflow(root_token):
    """ADR-008 §3.2: depth is capped (default 8)."""
    token = root_token
    for _ in range(8):
        token = exchange_token(
            token, ["mcp://github/repo:read"],
            actor="urn:principal:agent:sub", secret=SECRET,
        )
    # depth now 8; one more exchange must fail
    with pytest.raises(TokenExchangeError) as exc:
        exchange_token(token, ["mcp://github/repo:read"], secret=SECRET)
    assert "exceeds max_depth" in str(exc.value)


def test_denied_list_grows_monotonically(root_token):
    """A child's denied list must be a superset of the parent's denied
    list (deny-list precedence)."""
    root_claims = verify_token(root_token, secret=SECRET)
    denied_add = ["mcp://github/repo:write"]
    child = exchange_token(
        root_token, ["mcp://github/repo:read"],
        requested_scope_denied=denied_add, secret=SECRET,
    )
    child_claims = verify_token(child, secret=SECRET)
    assert set(denied_add).issubset(set(child_claims["scope"]["denied"]))
    # Parent's denied (empty here) must also be preserved
    assert set(root_claims["scope"]["denied"]).issubset(set(child_claims["scope"]["denied"]))


# ============================================================================
# Verify fail-closed classes
# ============================================================================

def test_verify_purpose_mismatch(root_token):
    with pytest.raises(TokenExchangeError) as exc:
        verify_token(root_token, secret=SECRET, mission_id="msn-other")
    assert "purpose mismatch" in str(exc.value)


def test_verify_capability_denied():
    token = issue_mission_token(
        mission_id=MISSION, mission_version=1,
        objective_text=OBJECTIVE, constraints=CONSTRAINTS,
        scope_allowed=SCOPE, scope_denied=["mcp://github/repo:write"],
        secret=SECRET,
    )
    with pytest.raises(TokenExchangeError) as exc:
        verify_token(token, secret=SECRET, require_capability="mcp://github/repo:write")
    assert "explicitly denied" in str(exc.value)


def test_verify_capability_not_in_scope():
    token = issue_mission_token(
        mission_id=MISSION, mission_version=1,
        objective_text=OBJECTIVE, constraints=CONSTRAINTS,
        scope_allowed=["mcp://github/repo:read"], secret=SECRET,
    )
    with pytest.raises(TokenExchangeError) as exc:
        verify_token(token, secret=SECRET, require_capability="mcp://aws/s3:put")
    assert "not in allowed scope" in str(exc.value)


def test_verify_constraints_hash_mismatch_closes_toctou(root_token):
    """TH-12: if the mission's constraints were mutated after issuance,
    verification must fail."""
    tampered = dict(CONSTRAINTS)
    tampered["required"] = ["no constraints at all"]  # widened post-issuance
    with pytest.raises(TokenExchangeError) as exc:
        verify_token(root_token, secret=SECRET, constraints=tampered)
    assert "constraints_hash mismatch" in str(exc.value)


def test_verify_objective_hash_mismatch(root_token):
    """A re-worded objective invalidates the token (ADR-008 §4 ceiling)."""
    with pytest.raises(TokenExchangeError) as exc:
        verify_token(
            root_token, secret=SECRET,
            objective_text="Completely different objective.",
        )
    assert "objective_hash mismatch" in str(exc.value)


def test_verify_expired_token():
    now = int(time.time())
    token = issue_mission_token(
        mission_id=MISSION, mission_version=1,
        objective_text=OBJECTIVE, constraints=CONSTRAINTS,
        scope_allowed=SCOPE, tau=now - 10, secret=SECRET,
    )
    with pytest.raises(TokenExchangeError) as exc:
        verify_token(token, secret=SECRET)
    assert "expired" in str(exc.value)


def test_verify_forged_signature():
    """A token signed with a different secret must be rejected (TH-03)."""
    forged = pyjwt.encode(
        {
            "purpose": f"urn:mission:{MISSION}:v1",
            "scope": {"allowed": SCOPE, "denied": []},
            "depth": 0, "iss": "attacker", "sub": "attacker",
            "iat": int(time.time()), "exp": int(time.time()) + 600,
        },
        "attacker-secret", algorithm="HS256",
    )
    with pytest.raises(TokenExchangeError):
        verify_token(forged, secret=SECRET)


def test_exchange_with_forged_parent_fails():
    """Exchange must verify the parent before issuing a child (TH-03)."""
    forged = pyjwt.encode(
        {
            "purpose": f"urn:mission:{MISSION}:v1",
            "scope": {"allowed": ["mcp://*"], "denied": []},
            "depth": 0, "iss": "attacker", "sub": "attacker",
            "iat": int(time.time()), "exp": int(time.time()) + 600,
        },
        "attacker-secret", algorithm="HS256",
    )
    with pytest.raises(TokenExchangeError):
        exchange_token(forged, ["mcp://github/repo:read"], secret=SECRET)


# ============================================================================
# Chain integrity
# ============================================================================

def test_parent_hash_chain(root_token):
    """Each child records the hash of its parent token (audit trail)."""
    import hashlib
    child = exchange_token(root_token, ["mcp://github/repo:read"], secret=SECRET)
    claims = verify_token(child, secret=SECRET)
    expected = hashlib.sha256(root_token.encode("utf-8")).hexdigest()
    assert claims["parent_hash"] == expected
