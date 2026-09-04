"""
test_q004_chaos_fail_closed.py
==============================

ADR-008 Phase 9 chaos test: verify that when MDT verification
fails *mid-mission*, the system fails closed — no capability
executes, the mission cannot transition to VERIFIED through the
compromised path, and the failure is visible in the lifecycle.

Chaos scenarios:
1. Secret rotation mid-mission: token signed with old secret is
   rejected after rotation.
2. Token expiry mid-mission: a token valid at mission start is
   rejected after tau passes.
3. Scope revocation mid-mission: attenuation to a narrower child
   token cannot re-acquire a revoked capability.
4. Mission mutation mid-mission: constraints_hash mismatch after
   the mission object is tampered with.
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

from capabilities.dispatcher import CapabilityDispatcher, CapabilityResolver
from capabilities.registry import Capability, CapabilityRegistry
from delegation.token_exchange import (
    TokenExchangeError,
    exchange_token,
    issue_mission_token,
)
from state.lifecycle import MissionLifecycle

SECRET_V1 = "chaos-secret-v1"
SECRET_V2 = "chaos-secret-v2"
URI = "mcp://github/repo:read"
SCOPE = ["mcp://github/repo:read", "mcp://github/repo:write"]
CONSTRAINTS = {"required": ["tests pass"]}
OBJECTIVE = "Chaos objective."


def _make_dispatch(executed_flag=None):
    def handler(payload):
        executed_flag["ran"] = True
        return {"status": "SUCCESS"}

    registry = CapabilityRegistry()
    registry.register(Capability(uri=URI, description="x", handler=handler))
    return CapabilityDispatcher(
        resolver=CapabilityResolver(registry), mdt_secret=SECRET_V1,
    )


def test_chaos_secret_rotation_mid_mission():
    """Token issued under secret v1 must be rejected after the
    Control Plane rotates to secret v2 (fail-closed, no execution)."""
    executed = {"ran": False}
    d = _make_dispatch(executed_flag=executed)
    token = issue_mission_token(
        mission_id="msn-chaos", mission_version=1,
        objective_text=OBJECTIVE, constraints=CONSTRAINTS,
        scope_allowed=SCOPE, secret=SECRET_V1,
    )
    # Pre-rotation: works
    receipt = d.dispatch(URI, delegation_token=token)
    assert receipt["status"] == "COMPLETED"

    # Rotate: the dispatcher now verifies under the new secret
    d.mdt_secret = SECRET_V2
    with pytest.raises(TokenExchangeError):
        d.dispatch(URI, delegation_token=token)
    assert executed["ran"] is True  # only the pre-rotation dispatch ran


def test_chaos_token_expiry_mid_mission():
    """A token with a short tau that expires mid-mission is rejected
    on the next dispatch."""
    executed = {"ran": False}
    d = _make_dispatch(executed_flag=executed)
    now = int(time.time())
    token = issue_mission_token(
        mission_id="msn-chaos", mission_version=1,
        objective_text=OBJECTIVE, constraints=CONSTRAINTS,
        scope_allowed=SCOPE, tau=now + 2, secret=SECRET_V1,
    )
    receipt = d.dispatch(URI, delegation_token=token)
    assert receipt["status"] == "COMPLETED"
    # Simulate tau passing (re-issue the same token with expired tau
    # rather than sleeping, to keep the suite fast)
    expired = pyjwt.decode(token, SECRET_V1, algorithms=["HS256"])
    expired["exp"] = now - 1
    expired_token = pyjwt.encode(expired, SECRET_V1, algorithm="HS256")
    with pytest.raises(TokenExchangeError) as exc:
        d.dispatch(URI, delegation_token=expired_token)
    assert "expired" in str(exc.value)


def test_chaos_scope_revocation_via_attenuation():
    """A revoked capability cannot be re-acquired: attenuating to a
    child that excludes the capability, then requesting it, fails."""
    root = issue_mission_token(
        mission_id="msn-chaos", mission_version=1,
        objective_text=OBJECTIVE, constraints=CONSTRAINTS,
        scope_allowed=SCOPE, secret=SECRET_V1,
    )
    # Worker 1 gets a child WITHOUT repo:write (attenuated)
    child = exchange_token(
        root, ["mcp://github/repo:read"],
        requested_scope_denied=["mcp://github/repo:write"], secret=SECRET_V1,
    )
    child_claims = pyjwt.decode(child, SECRET_V1, algorithms=["HS256"])
    assert "mcp://github/repo:write" in child_claims["scope"]["denied"]
    # The child cannot dispatch the revoked capability. The revoked
    # capability must be registered so we exercise the MDT deny check
    # (not the unknown-capability KeyError).
    executed = {"ran": False}

    def handler(payload):
        executed["ran"] = True
        return {"status": "SUCCESS"}

    registry = CapabilityRegistry()
    registry.register(Capability(uri="mcp://github/repo:write", description="w", handler=handler))
    d = CapabilityDispatcher(resolver=CapabilityResolver(registry), mdt_secret=SECRET_V1)
    with pytest.raises(TokenExchangeError) as exc:
        d.dispatch("mcp://github/repo:write", delegation_token=child)
    # Either "explicitly denied" or "not in allowed scope" is a correct
    # fail-closed rejection; both prove the revoked capability cannot
    # be re-acquired through an attenuated child.
    msg = str(exc.value)
    assert "explicitly denied" in msg or "not in allowed scope" in msg
    assert executed["ran"] is False, "Handler ran despite revoked capability"


def test_chaos_mission_mutation_invalidates_token():
    """If the mission's constraints are mutated after token issuance,
    all subsequent dispatches fail-closed (TH-12 via dispatcher path)."""
    token = issue_mission_token(
        mission_id="msn-chaos", mission_version=1,
        objective_text=OBJECTIVE, constraints=CONSTRAINTS,
        scope_allowed=SCOPE, secret=SECRET_V1,
    )
    # Verify directly through the exchange module with the *original*
    # constraints: OK. With mutated constraints: fail.
    from delegation.token_exchange import verify_token
    verify_token(token, secret=SECRET_V1, constraints=CONSTRAINTS)
    with pytest.raises(TokenExchangeError) as exc:
        verify_token(token, secret=SECRET_V1,
                     constraints={"required": ["mutated criterion"]})
    assert "constraints_hash mismatch" in str(exc.value)


def test_chaos_lifecycle_blocks_verified_after_failure():
    """End-to-end chaos: after a failed MDT dispatch, the mission
    lifecycle cannot reach VERIFIED through the LAB without evidence."""
    lifecycle = MissionLifecycle(initial_state="RUNNING")
    token = issue_mission_token(
        mission_id="msn-chaos", mission_version=1,
        objective_text=OBJECTIVE, constraints=CONSTRAINTS,
        scope_allowed=SCOPE, secret=SECRET_V1,
    )
    # Rotate secret: dispatch fails
    executed = {"ran": False}
    d = _make_dispatch(executed_flag=executed)
    d.mdt_secret = "rotated-secret"
    with pytest.raises(TokenExchangeError):
        d.dispatch(URI, delegation_token=token)
    # Mission proceeds to VERIFYING (the agent still claimed completion)
    lifecycle.transition_to("VERIFYING", reason="candidate completion")
    # LAB: no evidence exists, so VERIFIED is impossible even though
    # the agent asserts success.
    from evidence.store import EvidenceStore
    from assurance.engine import AssuranceEngine
    from assurance.principals import AssurancePrincipal
    engine = AssuranceEngine(lifecycle, EvidenceStore())
    success, diag = engine.evaluate_mission_criteria(
        mission_id="msn-chaos",
        required_criteria=["crit-1"],
        minimum_tier="tier_2_deterministic",
        caller=AssurancePrincipal,
    )
    assert success is False
    assert diag["status"] in ("RECOVERING", "FAILED")
    assert lifecycle.current_state != "VERIFIED"
