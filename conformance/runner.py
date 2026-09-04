import json
import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from runtime.engine import MissionEngine
from runtime.verifier import DeterministicTestVerifier

# ponytail: Automated Conformance Test Runner (Phase G).
# Validates any candidate runtime against SPEC-001 normative requirements.
# Produces an auditable JSON/text Conformance Report.

def run_conformance():
    test_cases_path = os.path.join(workspace, "conformance", "test_cases.json")
    with open(test_cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    print("==================================================")
    print(" RUNNING SPEC-001 CONFORMANCE TEST SUITE (PHASE G)")
    print("==================================================")

    for tc in cases:
        tc_id = tc["id"]
        tc_name = tc["name"]
        passed = False
        error_msg = None

        try:
            engine = MissionEngine()
            manifest_path = os.path.join(workspace, "examples", "INTELLIGENCE.yaml")
            mission_path = os.path.join(workspace, "examples", "mission.release.yaml")

            if tc_id == "TC-001":
                engine.load_manifest(manifest_path)
                passed = (engine.manifest is not None)

            elif tc_id == "TC-002":
                engine.load_mission(mission_path)
                passed = (engine.state == "READY")

            elif tc_id == "TC-003":
                engine.load_mission(mission_path)
                engine.authorize({
                    "id": "del-tc3", "principal": "urn:p", "delegate": "urn:d",
                    "purpose": "release-production", "scope": {"allowed_capabilities": ["*"]},
                    "valid_from": "2026-09-01T00:00:00Z", "expires_at": "2026-12-31T23:59:59Z"
                })
                engine.start()
                engine.finish_execution()
                passed = (engine.state == "VERIFYING" and engine.state != "VERIFIED")

            elif tc_id == "TC-004":
                engine.load_mission(mission_path)
                engine.authorize({
                    "id": "del-tc4", "principal": "urn:p", "delegate": "urn:d",
                    "purpose": "release-production", "scope": {"allowed_capabilities": ["*"]},
                    "valid_from": "2026-09-01T00:00:00Z", "expires_at": "2026-12-31T23:59:59Z"
                })
                engine.start()
                engine.finish_execution()
                # Without evidence, verify must fail
                v_fail = engine.evaluate_verification()
                assert not v_fail
                # Provide evidence
                verifier = DeterministicTestVerifier()
                for c in engine.mission["success"]["all"]:
                    ev = verifier.verify_callable("release-production", c, lambda: (True, "pass"))
                    engine.record_evidence(ev)
                v_pass = engine.evaluate_verification()
                passed = v_pass and (engine.state == "VERIFIED")

            elif tc_id == "TC-005":
                engine.load_mission(mission_path)
                engine.authorize({
                    "id": "del-tc5", "principal": "urn:p", "delegate": "urn:d",
                    "purpose": "release-production",
                    "scope": {
                        "allowed_capabilities": ["mcp://allowed/*"],
                        "denied_capabilities": ["mcp://allowed/blocked"]
                    },
                    "valid_from": "2026-09-01T00:00:00Z", "expires_at": "2026-12-31T23:59:59Z"
                })
                engine.start()
                # Allowed action
                engine.execute_action("mcp://allowed/tool1")
                # Denied action must raise PermissionError
                try:
                    engine.execute_action("mcp://allowed/blocked")
                    assert False, "Should have raised PermissionError"
                except PermissionError:
                    pass
                # Unlisted action must raise PermissionError
                try:
                    engine.execute_action("mcp://unknown/tool")
                    assert False, "Should have raised PermissionError"
                except PermissionError:
                    pass
                passed = True

            elif tc_id == "TC-006":
                budget_mission = {
                    "apiVersion": "intelligence.systems/v0alpha1",
                    "kind": "Mission",
                    "metadata": {"id": "m-budget", "version": 1},
                    "objective": {"outcome": "test budget"},
                    "success": {"all": ["c1"]},
                    "budget": {"tokens": {"max": 100}}
                }
                engine.load_mission(budget_mission)
                engine.authorize({
                    "id": "del-tc6", "principal": "urn:p", "delegate": "urn:d",
                    "purpose": "m-budget", "scope": {"allowed_capabilities": ["*"]},
                    "valid_from": "2026-09-01T00:00:00Z", "expires_at": "2026-12-31T23:59:59Z"
                })
                engine.start()
                engine.execute_action("mcp://t1", tokens=60)
                try:
                    engine.execute_action("mcp://t2", tokens=60)  # Total 120 > 100
                    assert False, "Should have raised RuntimeError on budget exhaustion"
                except RuntimeError:
                    passed = (engine.state == "NEEDS_INPUT")

            elif tc_id == "TC-007":
                states_seen = []
                states_seen.append(engine.state)  # DRAFT
                engine.load_mission(mission_path)
                states_seen.append(engine.state)  # READY
                engine.authorize({
                    "id": "del-tc7", "principal": "urn:p", "delegate": "urn:d",
                    "purpose": "release-production", "scope": {"allowed_capabilities": ["*"]},
                    "valid_from": "2026-09-01T00:00:00Z", "expires_at": "2026-12-31T23:59:59Z"
                })
                states_seen.append(engine.state)  # AUTHORIZED
                engine.start()
                states_seen.append(engine.state)  # RUNNING
                engine.finish_execution()
                states_seen.append(engine.state)  # VERIFYING
                passed = (states_seen == ["DRAFT", "READY", "AUTHORIZED", "RUNNING", "VERIFYING"])

            elif tc_id == "TC-008":
                engine.load_mission(mission_path)
                engine.authorize({
                    "id": "del-tc8", "principal": "urn:p", "delegate": "urn:d",
                    "purpose": "release-production", "scope": {"allowed_capabilities": ["*"]},
                    "valid_from": "2026-09-01T00:00:00Z", "expires_at": "2026-12-31T23:59:59Z"
                })
                engine.start()
                engine.execute_action("mcp://tool/x")
                traj = engine.trajectory
                has_valid_spans = all("timestamp" in e and "event_type" in e for e in traj)
                passed = (len(traj) >= 4 and has_valid_spans)

            elif tc_id == "TC-009":
                engine.load_mission(mission_path)
                engine.authorize({
                    "id": "del-tc9", "principal": "urn:p", "delegate": "urn:d",
                    "purpose": "release-production", "scope": {"allowed_capabilities": ["*"]},
                    "valid_from": "2026-09-01T00:00:00Z", "expires_at": "2026-12-31T23:59:59Z"
                })
                engine.start()
                engine.finish_execution()
                # Try recording Tier 0 (self-assertion)
                tier0_evidence = {
                    "id": "ev-self", "mission_id": "release-production",
                    "criterion_ref": "build_passed", "tier": "tier_0_self",
                    "verifier": {"type": "llm_judge", "identifier": "self"},
                    "result": "SATISFIED", "timestamp": "2026-09-03T20:00:00Z"
                }
                engine.record_evidence(tier0_evidence)
                # Must reject Tier 0 as insufficient
                v_res = engine.evaluate_verification()
                passed = (v_res is False and engine.state != "VERIFIED")

            elif tc_id == "TC-010":
                engine.load_mission(mission_path)
                engine.authorize({
                    "id": "del-tc10", "principal": "urn:p", "delegate": "urn:d",
                    "purpose": "release-production", "scope": {"allowed_capabilities": ["*"]},
                    "valid_from": "2026-09-01T00:00:00Z", "expires_at": "2026-12-31T23:59:59Z"
                })
                engine.start()
                engine.finish_execution()
                # Trigger verification failure
                engine.evaluate_verification()
                passed = (engine.state == "RECOVERING")

            elif tc_id == "TC-011":
                # TC-011: Delegation Expiration & Mid-flight Revocation
                engine.load_mission(mission_path)
                engine.authorize({
                    "id": "del-tc11", "principal": "urn:p", "delegate": "urn:d",
                    "purpose": "release-production", "scope": {"allowed_capabilities": ["*"]},
                    "valid_from": "2026-09-01T00:00:00Z", "expires_at": "2026-12-31T23:59:59Z"
                })
                engine.start()
                # Mid-flight revoke
                engine.revoke(reason="Revocation test")
                revoked_state = (engine.state == "REVOKED")
                action_blocked = False
                try:
                    engine.execute_action("mcp://test")
                except PermissionError:
                    action_blocked = True
                passed = revoked_state and action_blocked

            elif tc_id == "TC-012":
                # TC-012: Sub-delegation Monotonic Attenuation
                engine.load_mission(mission_path)
                engine.authorize({
                    "id": "del-tc12", "principal": "urn:p", "delegate": "urn:d",
                    "purpose": "release-production",
                    "scope": {"allowed_capabilities": ["mcp://repo/*"]},
                    "valid_from": "2026-09-01T00:00:00Z", "expires_at": "2026-12-31T23:59:59Z",
                    "max_delegation_depth": 2
                })
                # Attempt wider scope subdelegation -> must fail
                over_scoped_blocked = False
                try:
                    engine.create_subdelegation("urn:sub", "release-production", ["mcp://other/*"])
                except PermissionError:
                    over_scoped_blocked = True
                # Valid subdelegation
                child = engine.create_subdelegation("urn:sub", "release-production", ["mcp://repo/read"])
                valid_child = engine.validate_subdelegation(child)
                passed = over_scoped_blocked and valid_child and (child["max_delegation_depth"] == 1)

            elif tc_id == "TC-013":
                # TC-013: Multi-threaded Concurrency Invariants
                import concurrent.futures
                engine.load_mission(mission_path)
                engine.authorize({
                    "id": "del-tc13", "principal": "urn:p", "delegate": "urn:d",
                    "purpose": "release-production", "scope": {"allowed_capabilities": ["*"]},
                    "valid_from": "2026-09-01T00:00:00Z", "expires_at": "2026-12-31T23:59:59Z"
                })
                engine.start()
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                    futures = [pool.submit(lambda: engine.execute_action("mcp://tool", tokens=10)) for _ in range(20)]
                    [f.result() for f in futures]
                passed = (engine.budget_spent["actions"] == 20 and engine.budget_spent["tokens"] == 200)

            elif tc_id == "TC-014":
                # TC-014: Minimum Assurance Tier Enforcement
                engine.load_mission(mission_path)
                engine.mission["assurance"] = {
                    "verification": {"independence": "required", "minimum_tier": "tier_2_deterministic"}
                }
                engine.authorize({
                    "id": "del-tc14", "principal": "urn:p", "delegate": "urn:d",
                    "purpose": "release-production", "scope": {"allowed_capabilities": ["*"]},
                    "valid_from": "2026-09-01T00:00:00Z", "expires_at": "2026-12-31T23:59:59Z"
                })
                engine.start()
                engine.finish_execution()
                # Submit Tier 1 evidence when Tier 2 required
                for c in engine.mission["success"]["all"]:
                    engine.record_evidence({
                        "id": f"ev-{c}", "mission_id": "release-production",
                        "criterion_ref": c, "tier": "tier_1_model",
                        "verifier": {"type": "llm_judge", "identifier": "test-judge"},
                        "result": "SATISFIED", "timestamp": "2026-09-03T20:00:00Z"
                    })
                v_res = engine.evaluate_verification()
                tier1_rejected = (v_res is False)
                # Now submit Tier 2 evidence
                engine.state = "VERIFYING"
                verifier = DeterministicTestVerifier()
                for c in engine.mission["success"]["all"]:
                    engine.record_evidence(verifier.verify_callable("release-production", c, lambda: (True, "pass")))
                v_res2 = engine.evaluate_verification()
                passed = tier1_rejected and v_res2 and (engine.state == "VERIFIED")

        except Exception as e:
            passed = False
            error_msg = str(e)

        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] {tc_id}: {tc_name}")
        if error_msg:
            print(f"       Error: {error_msg}")

        results.append({
            "id": tc_id,
            "name": tc_name,
            "level": tc["level"],
            "status": status_str,
            "error": error_msg
        })

    total = len(results)
    passed_count = sum(1 for r in results if r["status"] == "PASS")
    pass_rate = (passed_count / total) * 100

    print("==================================================")
    print(f"CONFORMANCE SUMMARY: {passed_count}/{total} Passed ({pass_rate:.1f}%)")
    print("==================================================")

    # Export report to data/conformance_report.json
    rep_path = os.path.join(workspace, "data", "conformance_report.json")
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump({
            "suite_version": "0.1.0",
            "spec_ref": "SPEC-001-MISSION-CONTRACT-v0.1",
            "date": "2026-09-03",
            "pass_rate_pct": pass_rate,
            "results": results
        }, f, indent=2)

    return pass_rate == 100.0

if __name__ == "__main__":
    success = run_conformance()
    if not success:
        sys.exit(1)
