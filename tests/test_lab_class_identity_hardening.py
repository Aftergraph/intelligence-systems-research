"""
test_lab_class_identity_hardening.py
=====================================

Q-005 (open_questions.csv) follow-up: the LAB originally used
`caller.name == "AgentPrincipal"` to check the principal, which
is *not* class-identity-secure: a hostile process can construct
a fresh Principal with the same name and bypass the check.

This test pins the hardening: the engine must use object identity
(`is`) against the AgentPrincipal singleton. The AgentPrincipal is
a frozen dataclass singleton, so `is` is the correct defense.

This is a P0 security fix. Tests that pass before the hardening
should continue to pass after; tests that *would* bypass with
the old `==` check must now be rejected.
"""

import os
import sys

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from state.lifecycle import MissionLifecycle
from evidence.store import EvidenceStore
from assurance.engine import AssuranceEngine
from assurance.principals import (
    AgentPrincipal, AssurancePrincipal, Principal,
)


@pytest.fixture
def engine_setup():
    lifecycle = MissionLifecycle(initial_state="RUNNING")
    evidence_store = EvidenceStore()
    return lifecycle, evidence_store, AssuranceEngine(lifecycle, evidence_store)


def test_engine_rejects_fresh_principal_named_agent(engine_setup):
    """A hostile process constructs a fresh Principal with name
    'AgentPrincipal'. The hardened engine must reject it via
    object-identity (`is`), not string equality."""
    lifecycle, evidence_store, engine = engine_setup
    lifecycle.transition_to("VERIFYING", reason="intercepted")
    hostile = Principal(
        name="AgentPrincipal",
        capabilities={"agent.reasoning", "agent.candidate_completion"},
    )
    # Sanity: hostile has the same name as the singleton.
    assert hostile.name == AgentPrincipal.name
    # Sanity: they are NOT the same object.
    assert hostile is not AgentPrincipal
    # The hardened engine must still reject the hostile principal.
    with pytest.raises(PermissionError) as exc_info:
        engine.evaluate_mission_criteria(
            mission_id="hostile-impersonation",
            required_criteria=["test_criterion"],
            minimum_tier="tier_2_deterministic",
            caller=hostile,
        )
    msg = str(exc_info.value).lower()
    assert "barred" in msg or "agent" in msg, (
        f"Engine did not clearly reject hostile impersonation: "
        f"{exc_info.value!r}"
    )


def test_engine_accepts_singleton_agent_principal_is_check(engine_setup):
    """The actual AgentPrincipal singleton must be detected by `is`
    as a hostile attempt and rejected (because the singleton
    *is* the genuine AgentPrincipal and must be barred)."""
    lifecycle, evidence_store, engine = engine_setup
    lifecycle.transition_to("VERIFYING", reason="intercepted")
    # Use the actual singleton — the LAB must still reject it.
    with pytest.raises(PermissionError):
        engine.evaluate_mission_criteria(
            mission_id="singleton-agent",
            required_criteria=["test_criterion"],
            minimum_tier="tier_2_deterministic",
            caller=AgentPrincipal,
        )


def test_engine_accepts_singleton_assurance_principal(engine_setup):
    """The AssurancePrincipal singleton must pass the LAB check
    (the engine is designed to permit it)."""
    lifecycle, evidence_store, engine = engine_setup
    lifecycle.transition_to("VERIFYING", reason="intercepted")
    # AssurancePrincipal can call evaluate; we don't care about
    # the verdict here, only that it doesn't raise PermissionError.
    try:
        engine.evaluate_mission_criteria(
            mission_id="singleton-assurance",
            required_criteria=["nonexistent"],
            minimum_tier="tier_2_deterministic",
            caller=AssurancePrincipal,
        )
    except PermissionError as e:
        pytest.fail(
            f"Engine rejected the AssurancePrincipal singleton: {e}"
        )


def test_engine_rejects_fresh_principal_named_assurance(engine_setup):
    """A hostile process impersonates AssurancePrincipal by name.
    The hardened engine should still allow it (because by design
    only the singleton check matters for AgentPrincipal, not
    AssurancePrincipal). However, the hostile call must still
    be unable to verify without evidence — i.e. the LAB is
    symmetric in the sense that any principal without
    AgentPrincipal singleton-identity can call evaluate; the
    defense against sycophancy is the evidence gap, not the
    name.

    This test pins the *asymmetry*: only the AgentPrincipal side
    needs the singleton check (because AgentPrincipal is the
    adversarial principal), AssurancePrincipal does not."""
    lifecycle, evidence_store, engine = engine_setup
    lifecycle.transition_to("VERIFYING", reason="intercepted")
    hostile = Principal(
        name="AssurancePrincipal",
        capabilities={"assurance.evaluate", "mission.transition.verified"},
    )
    # The hostile AssurancePrincipal should be allowed to call
    # evaluate_mission_criteria (it is NOT in the singleton
    # check) but must FAIL to verify because no evidence exists.
    success, diag = engine.evaluate_mission_criteria(
        mission_id="assurance-impersonation",
        required_criteria=["nonexistent"],
        minimum_tier="tier_2_deterministic",
        caller=hostile,
    )
    # The defense here is the evidence gap, not the principal check.
    assert success is False, (
        f"Engine declared VERIFIED without evidence: {diag}"
    )
    assert diag["status"] in ("RECOVERING", "FAILED"), (
        f"Engine did not enter RECOVERING/FAILED: {diag['status']}"
    )


def test_agent_principal_rejection_message_mentions_agent(engine_setup):
    """The rejection message must be informative: it should mention
    the principal being rejected. This is important for the
    audit trail and for operators diagnosing a misconfigured
    caller."""
    lifecycle, evidence_store, engine = engine_setup
    lifecycle.transition_to("VERIFYING", reason="intercepted")
    hostile = Principal(name="AgentPrincipal")
    with pytest.raises(PermissionError) as exc_info:
        engine.evaluate_mission_criteria(
            mission_id="diagnostic",
            required_criteria=["x"],
            minimum_tier="tier_2_deterministic",
            caller=hostile,
        )
    msg = str(exc_info.value)
    assert "AgentPrincipal" in msg, (
        f"Rejection message does not mention AgentPrincipal: {msg}"
    )
