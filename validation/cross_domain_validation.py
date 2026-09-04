import datetime
import os
import sys

# Ensure workspace root is in sys.path
base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from validation.independent_runtime import IndependentMissionRuntime

# ponytail: Multi-Domain Independent Validation Harness.
# Executes 3 complete, realistic missions across SWE, Robotics, and Financial Data
# using ONLY the clean-room IndependentMissionRuntime.

def run_cross_domain_validation():
    results = {}

    # =========================================================================
    # Domain 1: Software Engineering (SWE)
    # =========================================================================
    print("Executing Domain 1: Software Engineering...")
    rt_swe = IndependentMissionRuntime()
    mission_swe = {
        "apiVersion": "intelligence.systems/v0alpha1",
        "kind": "Mission",
        "metadata": {"id": "swe-auth-fix-v1", "version": 1},
        "objective": {"outcome": "Fix JWT signature validation timing vulnerability"},
        "success": {"all": ["unit_tests_pass", "constant_time_verified"]},
        "budget": {"tokens": {"max": 25000}, "money": {"max": 1.0}},
        "recovery": {"retry_limit": 2}
    }
    rt_swe.load_mission(mission_swe)
    del_swe = {
        "id": "del-swe-01",
        "principal": "urn:principal:human:lead_dev",
        "delegate": "urn:agent:swe_code_agent",
        "purpose": "urn:mission:swe-auth-fix-v1:v1",
        "scope": {
            "allowed_capabilities": ["mcp://git/*", "mcp://test_runner/*"],
            "denied_capabilities": ["mcp://aws/iam:*", "mcp://prod_db/*"]
        },
        "valid_from": "2026-09-01T00:00:00Z",
        "expires_at": "2026-12-31T23:59:59Z"
    }
    rt_swe.grant_delegation(del_swe)
    rt_swe.start_execution()

    # Agent executes allowed actions
    rt_swe.invoke_capability("mcp://git/read_diff", tokens_used=120)
    rt_swe.invoke_capability("mcp://test_runner/execute", tokens_used=350)
    
    # Invariant 1: Declare complete transitions to VERIFYING
    rt_swe.declare_complete()
    assert rt_swe.state == "VERIFYING"

    # Submit Tier 2 deterministic evidence
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rt_swe.submit_evidence({
        "id": "ev-swe-1",
        "mission_id": "swe-auth-fix-v1",
        "criterion_ref": "unit_tests_pass",
        "tier": "tier_2_deterministic",
        "verifier": {"type": "test_harness", "identifier": "pytest-suite"},
        "result": "SATISFIED",
        "evidence_data": {"exit_code": 0, "passed": 42},
        "timestamp": now_iso
    })
    rt_swe.submit_evidence({
        "id": "ev-swe-2",
        "mission_id": "swe-auth-fix-v1",
        "criterion_ref": "constant_time_verified",
        "tier": "tier_2_deterministic",
        "verifier": {"type": "test_harness", "identifier": "timing-analyzer"},
        "result": "SATISFIED",
        "evidence_data": {"variance_ns": 0.12},
        "timestamp": now_iso
    })

    verified_swe = rt_swe.run_verification_gate()
    assert verified_swe is True
    assert rt_swe.state == "VERIFIED"
    results["software_engineering"] = {"status": "PASSED", "events": len(rt_swe.trajectory)}

    # =========================================================================
    # Domain 2: Autonomous Cyber-Physical Robotics
    # =========================================================================
    print("Executing Domain 2: Autonomous Robotics...")
    rt_rob = IndependentMissionRuntime()
    mission_rob = {
        "apiVersion": "intelligence.systems/v0alpha1",
        "kind": "Mission",
        "metadata": {"id": "rob-waypoint-nav-v1", "version": 1},
        "objective": {"outcome": "Navigate to waypoint B and deliver sensor payload safely"},
        "success": {"all": ["geofence_maintained", "battery_reserve_above_20pct", "sensor_receipt_signed"]},
        "budget": {"tokens": {"max": 15000}, "money": {"max": 2.5}},
        "recovery": {"retry_limit": 1}
    }
    rt_rob.load_mission(mission_rob)
    del_rob = {
        "id": "del-rob-01",
        "principal": "urn:principal:human:drone_operator",
        "delegate": "urn:agent:flight_controller",
        "purpose": "urn:mission:rob-waypoint-nav-v1:v1",
        "scope": {
            "allowed_capabilities": ["mcp://telemetry/read", "runtime://flight:navigate", "mcp://sensors/read"],
            "denied_capabilities": ["runtime://actuator:emergency_override"]
        },
        "valid_from": "2026-09-01T00:00:00Z",
        "expires_at": "2026-12-31T23:59:59Z"
    }
    rt_rob.grant_delegation(del_rob)
    rt_rob.start_execution()

    rt_rob.invoke_capability("mcp://telemetry/read", tokens_used=80)
    rt_rob.invoke_capability("runtime://flight:navigate", tokens_used=220)
    rt_rob.declare_complete()

    # Submit Tier 2 and Tier 3 hardware evidence
    rt_rob.submit_evidence({
        "id": "ev-rob-1",
        "mission_id": "rob-waypoint-nav-v1",
        "criterion_ref": "geofence_maintained",
        "tier": "tier_2_deterministic",
        "verifier": {"type": "test_harness", "identifier": "geofence_monitor"},
        "result": "SATISFIED",
        "evidence_data": {"max_boundary_deviation_meters": 0.04},
        "timestamp": now_iso
    })
    rt_rob.submit_evidence({
        "id": "ev-rob-2",
        "mission_id": "rob-waypoint-nav-v1",
        "criterion_ref": "battery_reserve_above_20pct",
        "tier": "tier_2_deterministic",
        "verifier": {"type": "test_harness", "identifier": "bms_telemetry"},
        "result": "SATISFIED",
        "evidence_data": {"remaining_battery_pct": 34.2},
        "timestamp": now_iso
    })
    rt_rob.submit_evidence({
        "id": "ev-rob-3",
        "mission_id": "rob-waypoint-nav-v1",
        "criterion_ref": "sensor_receipt_signed",
        "tier": "tier_3_attestation",
        "verifier": {"type": "cryptographic_service", "identifier": "hardware_tpm_signer"},
        "result": "SATISFIED",
        "evidence_data": {"signature": "ecdsa_secp256k1_3045022100..."},
        "timestamp": now_iso
    })

    verified_rob = rt_rob.run_verification_gate()
    assert verified_rob is True
    assert rt_rob.state == "VERIFIED"
    results["robotics"] = {"status": "PASSED", "events": len(rt_rob.trajectory)}

    # =========================================================================
    # Domain 3: Financial Data Engineering & Audited Ledger
    # =========================================================================
    print("Executing Domain 3: Financial Data Engineering...")
    rt_fin = IndependentMissionRuntime()
    mission_fin = {
        "apiVersion": "intelligence.systems/v0alpha1",
        "kind": "Mission",
        "metadata": {"id": "fin-ledger-audit-v1", "version": 1},
        "objective": {"outcome": "Reconcile daily settlement ledger against banking gateway"},
        "success": {"all": ["zero_balance_discrepancy", "c2pa_cryptographic_audit_provenance"]},
        "budget": {"tokens": {"max": 30000}, "money": {"max": 5.0}},
        "recovery": {"retry_limit": 1}
    }
    rt_fin.load_mission(mission_fin)
    del_fin = {
        "id": "del-fin-01",
        "principal": "urn:principal:human:chief_risk_officer",
        "delegate": "urn:agent:fin_reconciler",
        "purpose": "urn:mission:fin-ledger-audit-v1:v1",
        "scope": {
            "allowed_capabilities": ["mcp://ledger/query", "mcp://bank/transactions", "mcp://c2pa/sign"],
            "denied_capabilities": ["mcp://treasury/wire_transfer", "mcp://sec_edgar/submit_filing"]
        },
        "valid_from": "2026-09-01T00:00:00Z",
        "expires_at": "2026-12-31T23:59:59Z"
    }
    rt_fin.grant_delegation(del_fin)
    rt_fin.start_execution()

    rt_fin.invoke_capability("mcp://ledger/query", tokens_used=150)
    rt_fin.invoke_capability("mcp://bank/transactions", tokens_used=300)
    rt_fin.declare_complete()

    rt_fin.submit_evidence({
        "id": "ev-fin-1",
        "mission_id": "fin-ledger-audit-v1",
        "criterion_ref": "zero_balance_discrepancy",
        "tier": "tier_2_deterministic",
        "verifier": {"type": "test_harness", "identifier": "reconciliation_engine"},
        "result": "SATISFIED",
        "evidence_data": {"delta_cents": 0, "transactions_checked": 14520},
        "timestamp": now_iso
    })
    rt_fin.submit_evidence({
        "id": "ev-fin-2",
        "mission_id": "fin-ledger-audit-v1",
        "criterion_ref": "c2pa_cryptographic_audit_provenance",
        "tier": "tier_3_attestation",
        "verifier": {"type": "cryptographic_service", "identifier": "c2pa_vault_attestor"},
        "result": "SATISFIED",
        "evidence_data": {"c2pa_manifest_hash": "sha256:4f8e91b2c3a5..."},
        "timestamp": now_iso
    })

    verified_fin = rt_fin.run_verification_gate()
    assert verified_fin is True
    assert rt_fin.state == "VERIFIED"
    results["financial_data"] = {"status": "PASSED", "events": len(rt_fin.trajectory)}

    print("\n=== CROSS-DOMAIN INDEPENDENT VALIDATION COMPLETE ===")
    for domain, res in results.items():
        print(f"Domain: {domain:<25} | Status: {res['status']} | Recorded Trajectory Events: {res['events']}")

    return results

if __name__ == "__main__":
    run_cross_domain_validation()
