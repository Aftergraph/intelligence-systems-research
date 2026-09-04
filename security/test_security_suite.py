import datetime
import os
import sys
import pytest

# Ensure workspace root is in sys.path
base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from runtime.engine import MissionEngine
from runtime.verifier import DeterministicTestVerifier

# ponytail: Automated Security & Penetration Test Suite for SPEC-001.
# Validates runtime enforcement against the 10 threat vectors defined in SEC-001:
# Privilege Escalation, Delegation Forgery, Attenuation Bypass, Evidence Tampering,
# Budget Exhaustion, Objective Mutation, and Revocation.

@pytest.fixture
def initialized_engine():
    engine = MissionEngine()
    mission = {
        "apiVersion": "intelligence.systems/v0alpha1",
        "kind": "Mission",
        "metadata": {"id": "sec-mission-101", "version": 1},
        "objective": {"outcome": "Secure database index optimization"},
        "success": {"all": ["index_created", "latency_under_50ms"]},
        "budget": {
            "tokens": {"max": 10000},
            "money": {"max": 5.0}
        },
        "recovery": {"retry_limit": 1}
    }
    engine.load_mission(mission)
    delegation = {
        "id": "del-sec-101",
        "principal": "urn:principal:human:alice",
        "delegate": "urn:agent:db-optimizer",
        "purpose": "urn:mission:sec-mission-101:v1",
        "scope": {
            "allowed_capabilities": ["mcp://database/query", "mcp://database/explain"],
            "denied_capabilities": ["mcp://database/drop", "mcp://aws/iam:*"]
        },
        "valid_from": "2026-09-01T00:00:00Z",
        "expires_at": "2026-12-31T23:59:59Z"
    }
    engine.authorize(delegation)
    engine.start()
    return engine

def test_privilege_escalation_explicit_deny(initialized_engine):
    """TH-02: Ensure explicitly denied capability patterns are blocked."""
    engine = initialized_engine
    with pytest.raises(PermissionError) as excinfo:
        engine.execute_action("mcp://aws/iam:delete_role")
    assert "denied by pattern" in str(excinfo.value) or "denied" in str(excinfo.value)

    with pytest.raises(PermissionError) as excinfo:
        engine.execute_action("mcp://database/drop")
    assert "explicitly denied" in str(excinfo.value)

def test_unauthorized_capability_outside_scope(initialized_engine):
    """TH-02: Ensure capabilities not in the allowed scope are blocked."""
    engine = initialized_engine
    with pytest.raises(PermissionError) as excinfo:
        engine.execute_action("mcp://stripe/charge")
    assert "not authorized in delegation scope" in str(excinfo.value)

def test_delegation_purpose_mismatch_forgery():
    """TH-03: Ensure delegation token with forged or mismatched purpose is rejected."""
    engine = MissionEngine()
    mission = {
        "apiVersion": "intelligence.systems/v0alpha1",
        "kind": "Mission",
        "metadata": {"id": "legit-mission-42", "version": 1},
        "objective": {"outcome": "Legitimate maintenance"},
        "success": {"all": ["task_done"]}
    }
    engine.load_mission(mission)

    forged_delegation = {
        "id": "del-forged-999",
        "principal": "urn:principal:human:attacker",
        "delegate": "urn:agent:rogue-agent",
        "purpose": "urn:mission:evil-mission-666:v1",  # Mismatched purpose!
        "scope": {"allowed_capabilities": ["mcp://*"]},
        "valid_from": "2026-09-01T00:00:00Z",
        "expires_at": "2026-12-31T23:59:59Z"
    }
    with pytest.raises((AssertionError, ValueError)) as excinfo:
        engine.authorize(forged_delegation)
    assert "does not bind to mission" in str(excinfo.value)

def test_evidence_tampering_tier0_rejected(initialized_engine):
    """TH-05: Ensure Tier 0 self-assertion cannot satisfy verification (Invariant 1 & 2)."""
    engine = initialized_engine
    engine.finish_execution()
    assert engine.state == "VERIFYING"

    # Agent fabricates a Tier 0 self-assertion with valid schema structure
    fake_evidence = {
        "id": "ev-fake-01",
        "mission_id": "sec-mission-101",
        "criterion_ref": "index_created",
        "tier": "tier_0_self",
        "verifier": {
            "type": "llm_judge",
            "identifier": "urn:agent:db-optimizer"
        },
        "result": "SATISFIED",
        "evidence_data": {"claim": "I created the index successfully"},
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    engine.record_evidence(fake_evidence)

    # Invariant 2: Tier 0 must be rejected by evaluate_verification
    verified = engine.evaluate_verification()
    assert verified is False
    assert engine.state in ("RECOVERING", "FAILED")
    assert engine.state != "VERIFIED"

def test_evidence_tampering_failed_result_rejected(initialized_engine):
    """TH-05: Ensure failed evidence items cannot transition to VERIFIED."""
    engine = initialized_engine
    engine.finish_execution()

    verifier = DeterministicTestVerifier()
    failed_ev = verifier.verify_callable(
        mission_id="sec-mission-101",
        criterion_ref="index_created",
        test_fn=lambda: (False, "Syntax error creating index")
    )
    engine.record_evidence(failed_ev)

    verified = engine.evaluate_verification()
    assert verified is False
    assert engine.state in ("RECOVERING", "FAILED")

def test_budget_exhaustion_containment(initialized_engine):
    """TH-08: Ensure budget exhaustion triggers immediate halt into NEEDS_INPUT."""
    engine = initialized_engine
    
    # Execute normal allowed action
    engine.execute_action("mcp://database/query", tokens=500, cost_usd=0.05)
    assert engine.budget_spent["tokens"] == 500

    # Attempt action exceeding budget ceiling (max tokens = 10,000)
    with pytest.raises(RuntimeError) as excinfo:
        engine.execute_action("mcp://database/explain", tokens=12000, cost_usd=0.01)
    assert "Token budget exhausted" in str(excinfo.value)
    assert engine.state == "NEEDS_INPUT"

def test_objective_immutability(initialized_engine):
    """TH-01: Ensure mission objective is immutable during execution and tampering is blocked."""
    engine = initialized_engine
    
    # Tampering attempt by adversary modifying the objective
    engine.mission["objective"]["outcome"] = "tampered malicious objective"
    
    with pytest.raises(PermissionError) as excinfo:
        engine.execute_action("mcp://database/query", tokens=100, cost_usd=0.01)
    assert "tampering detected" in str(excinfo.value)
    assert engine.state == "FAILED"

def test_delegation_token_expiration():
    """TH-04: Ensure expired delegation tokens are blocked."""
    engine = MissionEngine()
    mission = {
        "apiVersion": "intelligence.systems/v0alpha1",
        "kind": "Mission",
        "metadata": {"id": "m-exp-01", "version": 1},
        "objective": {"outcome": "Test token expiration"},
        "success": {"all": ["task_done"]}
    }
    engine.load_mission(mission)
    expired_delegation = {
        "id": "del-exp-01",
        "principal": "urn:principal:human:alice",
        "delegate": "urn:agent:worker",
        "purpose": "urn:mission:m-exp-01:v1",
        "scope": {"allowed_capabilities": ["mcp://*"]},
        "valid_from": "2020-01-01T00:00:00Z",
        "expires_at": "2020-01-02T00:00:00Z"
    }
    engine.authorize(expired_delegation)
    engine.start()
    
    with pytest.raises(PermissionError) as excinfo:
        engine.execute_action("mcp://database/query")
    assert "expired" in str(excinfo.value)

def test_delegation_token_not_yet_valid():
    """TH-04: Ensure tokens not yet valid are blocked."""
    engine = MissionEngine()
    mission = {
        "apiVersion": "intelligence.systems/v0alpha1",
        "kind": "Mission",
        "metadata": {"id": "m-future-01", "version": 1},
        "objective": {"outcome": "Test future token"},
        "success": {"all": ["task_done"]}
    }
    engine.load_mission(mission)
    future_delegation = {
        "id": "del-future-01",
        "principal": "urn:principal:human:alice",
        "delegate": "urn:agent:worker",
        "purpose": "urn:mission:m-future-01:v1",
        "scope": {"allowed_capabilities": ["mcp://*"]},
        "valid_from": "2030-01-01T00:00:00Z",
        "expires_at": "2030-01-02T00:00:00Z"
    }
    engine.authorize(future_delegation)
    engine.start()
    
    with pytest.raises(PermissionError) as excinfo:
        engine.execute_action("mcp://database/query")
    assert "not yet valid" in str(excinfo.value)

def test_authority_revocation_midflight(initialized_engine):
    """TH-04: Ensure revoking authority mid-flight halts execution and blocks all actions."""
    engine = initialized_engine
    assert engine.state == "RUNNING"
    
    # Mid-flight revocation by operator
    engine.revoke(reason="Security compromise suspected")
    assert engine.state == "REVOKED"
    
    with pytest.raises(PermissionError) as excinfo:
        engine.execute_action("mcp://database/query")
    assert "revoked" in str(excinfo.value)

def test_subdelegation_scope_attenuation(initialized_engine):
    """TH-02 / Invariant 3: Subdelegation must attenuate scope and cannot exceed parent."""
    engine = initialized_engine
    
    # Parent scope allows: ["mcp://database/query", "mcp://database/explain"]
    # Child attempting to subdelegate unauthorized capability
    with pytest.raises(PermissionError) as excinfo:
        engine.create_subdelegation(
            subagent_urn="urn:agent:subagent-1",
            purpose="urn:mission:sec-mission-101:v1",
            allowed_capabilities=["mcp://database/query", "mcp://aws/s3:delete"]
        )
    assert "exceeds parent scope" in str(excinfo.value)

    # Valid subdelegation
    child = engine.create_subdelegation(
        subagent_urn="urn:agent:subagent-1",
        purpose="urn:mission:sec-mission-101:v1",
        allowed_capabilities=["mcp://database/query"]
    )
    assert child["max_delegation_depth"] == 0
    assert engine.validate_subdelegation(child) is True

def test_minimum_assurance_tier_enforcement():
    """TH-05 / NIST AI 200-2: Tier 1 model evaluation rejected when Tier 2 required."""
    engine = MissionEngine()
    mission = {
        "apiVersion": "intelligence.systems/v0alpha1",
        "kind": "Mission",
        "metadata": {"id": "m-assurance-01", "version": 1},
        "objective": {"outcome": "High-assurance release"},
        "success": {"all": ["lint_passed", "tests_passed"]},
        "assurance": {
            "verification": {
                "independence": "required",
                "minimum_tier": "tier_2_deterministic"
            }
        },
        "recovery": {"retry_limit": 0}
    }
    engine.load_mission(mission)
    delegation = {
        "id": "del-ass-01",
        "principal": "urn:principal:human:test",
        "delegate": "urn:agent:dev",
        "purpose": "urn:mission:m-assurance-01:v1",
        "scope": {"allowed_capabilities": ["*"]},
        "valid_from": "2026-09-03T00:00:00Z",
        "expires_at": "2026-09-04T00:00:00Z"
    }
    engine.authorize(delegation)
    engine.start()
    engine.finish_execution()
    
    # Submit Tier 1 evidence (Model evaluation)
    tier1_ev = {
        "id": "ev-model-judge",
        "mission_id": "m-assurance-01",
        "criterion_ref": "lint_passed",
        "tier": "tier_1_model",
        "verifier": {"type": "llm_judge", "identifier": "evaluator-gpt4"},
        "result": "SATISFIED",
        "timestamp": "2026-09-03T21:00:00Z"
    }
    engine.record_evidence(tier1_ev)
    
    # Must fail because minimum_tier is tier_2_deterministic
    verified = engine.evaluate_verification()
    assert verified is False
    assert engine.state == "FAILED"

def test_concurrent_execution_thread_safety(initialized_engine):
    """TH-10: Multi-threaded simultaneous execution must maintain thread safety and budget integrity."""
    import concurrent.futures
    engine = initialized_engine
    
    def run_step(i):
        return engine.execute_action("mcp://database/query", tokens=10, cost_usd=0.001)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run_step, i) for i in range(50)]
        results = [f.result() for f in futures]
    
    assert len(results) == 50
    assert engine.budget_spent["actions"] == 50
    assert engine.budget_spent["tokens"] == 500
    assert round(engine.budget_spent["usd"], 3) == 0.050
