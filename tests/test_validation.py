import os
import sys
import pytest

# Ensure workspace root is in sys.path
base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from validation.independent_runtime import IndependentMissionRuntime
from validation.cross_domain_validation import run_cross_domain_validation

# ponytail: Tests verifying the clean-room independent runtime and cross-domain validation.

def test_independent_runtime_invariants():
    rt = IndependentMissionRuntime()
    mission = {
        "apiVersion": "intelligence.systems/v0alpha1",
        "kind": "Mission",
        "metadata": {"id": "indep-test-01", "version": 1},
        "objective": {"outcome": "Clean-room test execution"},
        "success": {"all": ["code_compiled", "tests_passed"]},
        "budget": {"tokens": {"max": 5000}, "money": {"max": 1.0}},
        "recovery": {"retry_limit": 1}
    }
    rt.load_mission(mission)
    assert rt.state == "READY"

    delegation = {
        "id": "del-indep-01",
        "principal": "urn:principal:human:test",
        "delegate": "urn:agent:indep_worker",
        "purpose": "urn:mission:indep-test-01:v1",
        "scope": {
            "allowed_capabilities": ["mcp://build/*", "mcp://test/*"],
            "denied_capabilities": ["mcp://prod/*"]
        },
        "valid_from": "2026-09-01T00:00:00Z",
        "expires_at": "2026-12-31T23:59:59Z"
    }
    rt.grant_delegation(delegation)
    assert rt.state == "AUTHORIZED"

    rt.start_execution()
    assert rt.state == "RUNNING"

    # Capability execution
    res = rt.invoke_capability("mcp://build/compile", tokens_used=100)
    assert res["status"] == "SUCCESS"

    # Blocked capability
    with pytest.raises(PermissionError):
        rt.invoke_capability("mcp://prod/deploy")

    # Invariant 1: Declare complete -> VERIFYING
    rt.declare_complete()
    assert rt.state == "VERIFYING"

    # Invariant 2: Run verification without evidence -> Fails
    verified = rt.run_verification_gate()
    assert verified is False
    assert rt.state in ("RECOVERING", "FAILED")

    # Submit qualifying evidence
    rt.submit_evidence({
        "id": "ev-01",
        "mission_id": "indep-test-01",
        "criterion_ref": "code_compiled",
        "tier": "tier_2_deterministic",
        "verifier": {"type": "compiler", "identifier": "clang-18"},
        "result": "SATISFIED",
        "timestamp": "2026-09-03T22:00:00Z"
    })
    rt.submit_evidence({
        "id": "ev-02",
        "mission_id": "indep-test-01",
        "criterion_ref": "tests_passed",
        "tier": "tier_2_deterministic",
        "verifier": {"type": "test_harness", "identifier": "pytest"},
        "result": "SATISFIED",
        "timestamp": "2026-09-03T22:00:00Z"
    })

    verified_pass = rt.run_verification_gate()
    assert verified_pass is True
    assert rt.state == "VERIFIED"

def test_cross_domain_validation_suite():
    results = run_cross_domain_validation()
    assert results["software_engineering"]["status"] == "PASSED"
    assert results["robotics"]["status"] == "PASSED"
    assert results["financial_data"]["status"] == "PASSED"

def test_independent_runtime_lifecycle():
    rt = IndependentMissionRuntime()
    mission = {
        "apiVersion": "intelligence.systems/v0alpha1",
        "kind": "Mission",
        "metadata": {"id": "indep-life-01", "version": 1},
        "objective": {"outcome": "Lifecycle verification"},
        "success": {"all": ["step1"]}
    }
    rt.load_mission(mission)
    delegation = {
        "id": "del-life-01",
        "principal": "urn:principal:human:test",
        "delegate": "urn:agent:worker",
        "purpose": "urn:mission:indep-life-01:v1",
        "scope": {"allowed_capabilities": ["*"]},
        "valid_from": "2026-09-03T00:00:00Z",
        "expires_at": "2026-09-04T00:00:00Z"
    }
    rt.grant_delegation(delegation)
    rt.start_execution()
    
    # Pause & Resume
    rt.pause()
    assert rt.state == "PAUSED"
    with pytest.raises(RuntimeError):
        rt.invoke_capability("mcp://test")
    rt.resume()
    assert rt.state == "RUNNING"
    
    # Revoke
    rt.revoke()
    assert rt.state == "REVOKED"
    with pytest.raises(PermissionError):
        rt.invoke_capability("mcp://test")

def test_independent_runtime_subdelegation():
    rt = IndependentMissionRuntime()
    rt.delegation = {
        "id": "del-p",
        "principal": "urn:p",
        "delegate": "urn:d",
        "purpose": "p",
        "scope": {"allowed_capabilities": ["mcp://read/*"]},
        "valid_from": "2026-09-03T00:00:00Z",
        "expires_at": "2026-09-04T00:00:00Z"
    }
    valid_sub = {
        "id": "del-c",
        "principal": "urn:d",
        "delegate": "urn:sub",
        "purpose": "p",
        "scope": {"allowed_capabilities": ["mcp://read/file"]},
        "valid_from": "2026-09-03T00:00:00Z",
        "expires_at": "2026-09-04T00:00:00Z"
    }
    assert rt.validate_subdelegation(valid_sub) is True

    invalid_sub = {
        "id": "del-c2",
        "principal": "urn:d",
        "delegate": "urn:sub2",
        "purpose": "p",
        "scope": {"allowed_capabilities": ["mcp://write/file"]},
        "valid_from": "2026-09-03T00:00:00Z",
        "expires_at": "2026-09-04T00:00:00Z"
    }
    assert rt.validate_subdelegation(invalid_sub) is False
