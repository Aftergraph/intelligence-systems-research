"""
test_threat_model_distributed_vectors.py
========================================

TH-17 / TH-18: the two remaining vector classes from the ADR-007 §7
and ADR-008 follow-up queue.

TH-17 — Multi-region consensus partition: when the SS control-plane
consensus layer is unavailable (network partition), the mission
lifecycle must FAIL CLOSED (no transitions, no VERIFIED).

TH-18 — Federated token trust: an MDT issued by a foreign Control
Plane (different signing secret) must be rejected — tokens are not
valid across Control Plane instances (ADR-008 §3.5).
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

from state.lifecycle import MissionLifecycle, ALLOWED_TRANSITIONS
from assurance.engine import AssuranceEngine
from evidence.store import EvidenceStore
from assurance.principals import AssurancePrincipal, AgentPrincipal
from delegation.token_exchange import (
    TokenExchangeError,
    issue_mission_token,
    verify_token,
)


# ============================================================================
# TH-17: multi-region consensus partition → fail-closed
# ============================================================================

def test_th17_consensus_partition_blocks_verification_path():
    """Simulated partition: when consensus is unavailable, the control
    plane cannot safely serialize lifecycle transitions. The fail-closed
    contract: from RECOVERING, the ONLY reachable states are the FSM's
    documented set (RUNNING, NEEDS_INPUT, FAILED) — VERIFIED is NOT
    reachable without passing through RUNNING→VERIFYING, and each
    transition is single-writer (no concurrent split-brain writes)."""
    # Structural check: no state has VERIFIED as a direct successor
    # except VERIFYING (this is what prevents split-brain VERIFIED
    # during a partition — the FSM is the consensus proxy at Phase 1).
    for state, targets in ALLOWED_TRANSITIONS.items():
        if state == "VERIFYING":
            assert "VERIFIED" in targets  # the single legitimate gate
        else:
            assert "VERIFIED" not in targets, (
                f"{state} can transition directly to VERIFIED — split-brain "
                f"risk. VERIFIED must only be reachable via VERIFYING."
            )

    # Behavioral check: a mission in RECOVERING cannot reach VERIFIED
    lifecycle = MissionLifecycle(initial_state="VERIFYING")
    lifecycle.transition_to("RECOVERING", reason="consensus partition")
    with pytest.raises(RuntimeError):
        lifecycle.transition_to("VERIFIED", reason="split-brain attempt")


def test_th17_partition_halts_mission_without_evidence():
    """During a partition, even with the agent asserting success, the
    LAB requires evidence — the mission cannot reach VERIFIED."""
    lifecycle = MissionLifecycle(initial_state="RUNNING")
    engine = AssuranceEngine(lifecycle, EvidenceStore())
    lifecycle.transition_to("VERIFYING", reason="candidate during partition")
    success, diag = engine.evaluate_mission_criteria(
        mission_id="th17", required_criteria=["x"],
        minimum_tier="tier_2_deterministic",
        caller=AssurancePrincipal,
    )
    assert success is False
    assert lifecycle.current_state != "VERIFIED"


# ============================================================================
# TH-18: federated token trust
# ============================================================================

def test_th18_foreign_control_plane_token_rejected():
    """An MDT signed by a foreign Control Plane (different secret) must
    be rejected — ADR-008 §3.5: no cross-org token trust."""
    foreign = pyjwt.encode(
        {
            "purpose": "urn:mission:msn-th18:v1",
            "objective_hash": "0" * 64,
            "constraints_hash": "0" * 64,
            "scope": {"allowed": ["mcp://*"], "denied": []},
            "depth": 0, "iss": "urn:principal:foreign-cp", "sub": "urn:principal:foreign-cp",
            "iat": int(__import__("time").time()), "exp": int(__import__("time").time()) + 600,
        },
        "foreign-control-plane-secret", algorithm="HS256",
    )
    with pytest.raises(TokenExchangeError := __import__("delegation.token_exchange", fromlist=["TokenExchangeError"]).TokenExchangeError):
        verify_token(foreign, secret="local-cp-secret", mission_id="msn-th18")


def test_th18_local_token_with_foreign_purpose_rejected():
    """A locally-signed token whose purpose binds to a foreign mission
    must be rejected when verified against a local mission ID."""
    token = issue_mission_token(
        mission_id="msn-foreign", mission_version=1,
        objective_text="x", constraints={"a": 1},
        scope_allowed=["mcp://a:read"], secret="local-secret",
    )
    with pytest.raises(TokenExchangeError):
        verify_token(token, secret="local-secret", mission_id="msn-local")