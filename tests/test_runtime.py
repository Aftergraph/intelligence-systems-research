import os
import sys

# Ensure workspace root is in sys.path
base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from runtime.engine import MissionEngine
from runtime.verifier import DeterministicTestVerifier

# ponytail: Minimal runnable assert-based check for Reference Runtime v0.1.
# Verifies Invariant 1 (Complete != Verified) and Invariant 2 (Evidence-Gated Completion).
# No external test runner required.

def test_full_runtime():
    example_mission_path = os.path.join(workspace, "examples", "mission.release.yaml")
    example_manifest_path = os.path.join(workspace, "examples", "INTELLIGENCE.yaml")

    engine = MissionEngine()

    # 1. Manifest & Mission Loading
    engine.load_manifest(example_manifest_path)
    engine.load_mission(example_mission_path)
    assert engine.state == "READY", f"Expected state READY, got {engine.state}"

    # 2. Authorization
    delegation = {
        "id": "del-release-42",
        "principal": "urn:principal:human:jonas",
        "delegate": "urn:agent:release-agent",
        "purpose": "urn:mission:release-production:v1",
        "scope": {
            "allowed_capabilities": ["mcp://github/*", "mcp://k8s/deploy", "skill://*"],
            "denied_capabilities": ["mcp://aws/iam:*"]
        },
        "valid_from": "2026-09-01T00:00:00Z",
        "expires_at": "2026-12-31T23:59:59Z",
        "allow_redelegation": False,
        "max_delegation_depth": 1
    }
    engine.authorize(delegation)
    assert engine.state == "AUTHORIZED"

    # 3. Execution Start
    engine.start()
    assert engine.state == "RUNNING"

    # 4. Authorized actions
    res1 = engine.execute_action("mcp://github/repo:write", tokens=100, cost_usd=0.01)
    assert res1["status"] == "SUCCESS"

    res2 = engine.execute_action("mcp://k8s/deploy", tokens=150, cost_usd=0.02)
    assert res2["status"] == "SUCCESS"

    # 5. Authority Policy Test: Denied capability must raise PermissionError
    try:
        engine.execute_action("mcp://aws/iam:delete", tokens=50)
        raise AssertionError("Expected PermissionError for denied capability!")
    except PermissionError:
        pass  # Expected

    # 6. Unauthorized capability (not in allowed list) must raise PermissionError
    try:
        engine.execute_action("mcp://stripe/charge", tokens=50)
        raise AssertionError("Expected PermissionError for unauthorized capability!")
    except PermissionError:
        pass  # Expected

    # 7. Agent finishes execution -> Invariant 1: State must be VERIFYING, NOT VERIFIED
    engine.finish_execution()
    assert engine.state == "VERIFYING", f"Expected state VERIFYING, got {engine.state}"

    # 8. False Completion Prevention Test:
    # If verifier evaluates without satisfactory evidence -> Invariant 2 prevents VERIFIED
    verified = engine.evaluate_verification()
    assert not verified, "evaluate_verification must return False when evidence is missing!"
    assert engine.state in ("RECOVERING", "FAILED"), f"Expected RECOVERING/FAILED, got {engine.state}"
    print("SUCCESS: Invariant 1 & 2 validated - False completion prevented.")

    # 9. Now provide qualifying Tier 2 evidence for all criteria and verify transition
    engine.state = "VERIFYING"  # reset to verifying for retry
    verifier = DeterministicTestVerifier()

    required_criteria = [
        "build_passed",
        "tests_passed",
        "security_scan_passed",
        "deployment_completed",
        "production_health_verified"
    ]

    for crit in required_criteria:
        ev = verifier.verify_callable(
            mission_id="release-production",
            criterion_ref=crit,
            test_fn=lambda: (True, "All checks passed deterministically")
        )
        engine.record_evidence(ev)

    # Re-evaluate verification
    verified = engine.evaluate_verification()
    assert verified, "evaluate_verification must return True when all criteria satisfied!"
    assert engine.state == "VERIFIED", f"Expected state VERIFIED, got {engine.state}"
    print("SUCCESS: Ground-truth verified outcome achieved.")

    # 10. Check metrics & Control Plane Tax
    metrics = engine.get_metrics()
    assert metrics["is_verified"] is True
    assert metrics["control_plane_tax"] > 0.0
    print(f"SUCCESS: Metrics validated: CPVO metrics recorded, Control Plane Tax = {metrics['control_plane_tax']:.2%}")

if __name__ == "__main__":
    test_full_runtime()
