import datetime
import json
import os
import sys
import time

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from runtime.engine import MissionEngine
from runtime.verifier import DeterministicTestVerifier
from runtime.storage import TrajectoryStorage
from runtime.policy import PolicyEngine

# ponytail: Phase H Enterprise Pilot Integration Suite.
# Demonstrates SPEC-001 deployed across 3 high-impact enterprise operational scenarios:
# 1. GitOps Production Deployment & Canary Verification
# 2. Financial Batch ETL Data Pipeline with Budget Cap
# 3. SRE Incident Remediation with Attenuated Authority

def run_gitops_pilot():
    print("\n--- PILOT 1: GITOPS PRODUCTION CANARY RELEASE ---")
    mission = {
        "apiVersion": "intelligence.systems/v0alpha1",
        "kind": "Mission",
        "metadata": {"id": "pilot-gitops-release", "version": 1},
        "objective": {"outcome": "Safely promote v2.4.0 image to staging and verify canary metrics before production promotion."},
        "success": {
            "all": ["unit_tests_pass", "canary_health_verified", "staging_metrics_green"]
        },
        "constraints": {"max_error_rate": 0.005, "canary_window_sec": 5},
        "budget": {"tokens": {"max": 50000}, "money": {"max": 1.0}}
    }

    delegation = {
        "id": "del-gitops-01",
        "principal": "urn:authority:cd-pipeline",
        "delegate": "urn:agent:release-bot",
        "purpose": "pilot-gitops-release",
        "scope": {
            "allowed_capabilities": ["mcp://k8s/deploy_canary", "mcp://prometheus/query_metrics", "mcp://git/tag_release"],
            "denied_capabilities": ["mcp://k8s/delete_namespace", "mcp://aws/delete_cluster"]
        },
        "valid_from": "2026-09-01T00:00:00Z",
        "expires_at": "2026-09-30T00:00:00Z"
    }

    engine = MissionEngine()
    engine.load_mission(mission)
    engine.authorize(delegation)
    engine.start()

    # Step 1: Deploy canary
    engine.execute_action("mcp://k8s/deploy_canary", {"image": "svc-auth:v2.4.0", "replicas": 2}, tokens=120, cost_usd=0.005)
    
    # Step 2: Query prometheus
    engine.execute_action("mcp://prometheus/query_metrics", {"query": "http_requests_5xx_rate"}, tokens=80, cost_usd=0.002)

    # Step 3: Agent finishes execution
    engine.finish_execution()
    assert engine.state == "VERIFYING", "Must transition to VERIFYING, not directly to VERIFIED"

    # Step 4: Supply Tier 2 deterministic verification receipts
    engine.record_evidence({
        "id": "ev-gitops-1", "mission_id": "pilot-gitops-release",
        "criterion_ref": "unit_tests_pass", "tier": "tier_2_deterministic",
        "verifier": {"type": "test_harness", "identifier": "pytest-k8s"},
        "result": "SATISFIED", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })
    engine.record_evidence({
        "id": "ev-gitops-2", "mission_id": "pilot-gitops-release",
        "criterion_ref": "canary_health_verified", "tier": "tier_2_deterministic",
        "verifier": {"type": "test_harness", "identifier": "synthetic-canary-prober"},
        "result": "SATISFIED", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })
    engine.record_evidence({
        "id": "ev-gitops-3", "mission_id": "pilot-gitops-release",
        "criterion_ref": "staging_metrics_green", "tier": "tier_2_deterministic",
        "verifier": {"type": "test_harness", "identifier": "datadog-slas"},
        "result": "SATISFIED", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })

    verified = engine.evaluate_verification()
    assert verified is True
    assert engine.state == "VERIFIED"
    print("[PASS] GitOps Pilot: Successfully verified with 3 Tier-2 deterministic receipts.")
    return {"pilot": "gitops_release", "status": "VERIFIED", "events": len(engine.trajectory)}

def run_data_pipeline_pilot():
    print("\n--- PILOT 2: FINANCIAL BATCH ETL PIPELINE (BUDGET ENFORCEMENT) ---")
    mission = {
        "apiVersion": "intelligence.systems/v0alpha1",
        "kind": "Mission",
        "metadata": {"id": "pilot-etl-financial", "version": 1},
        "objective": {"outcome": "Extract, transform, and partition transaction records with strict cost ceiling."},
        "success": {"all": ["schema_validated", "row_count_matched", "partition_sealed"]},
        "budget": {"money": {"max": 0.05}, "tokens": {"max": 10000}}
    }

    delegation = {
        "id": "del-etl-01",
        "principal": "urn:authority:data-eng",
        "delegate": "urn:agent:etl-worker",
        "purpose": "pilot-etl-financial",
        "scope": {"allowed_capabilities": ["mcp://s3/*", "mcp://duckdb/*"]},
        "valid_from": "2026-09-01T00:00:00Z",
        "expires_at": "2026-09-30T00:00:00Z"
    }

    engine = MissionEngine()
    engine.load_mission(mission)
    engine.authorize(delegation)
    engine.start()

    # Worker actions within budget
    engine.execute_action("mcp://s3/get_batch", {"batch_id": "tx-2026-09"}, tokens=400, cost_usd=0.01)
    engine.execute_action("mcp://duckdb/transform", {"partitions": 4}, tokens=500, cost_usd=0.015)

    # Simulate adversarial runaway cost attempt ($0.06 > $0.05 max)
    cost_blocked = False
    try:
        engine.execute_action("mcp://duckdb/expensive_join", {}, tokens=2000, cost_usd=0.06)
    except RuntimeError as e:
        cost_blocked = True
        assert engine.state == "NEEDS_INPUT"

    assert cost_blocked is True, "Must block action exceeding budget"
    print("[PASS] Data Pipeline Pilot: Budget ceiling strictly contained runaway query.")
    return {"pilot": "data_pipeline", "status": "BUDGET_CONTAINED", "events": len(engine.trajectory)}

def run_sre_incident_pilot():
    print("\n--- PILOT 3: SRE INCIDENT REMEDIATION & OPERATOR TAKEOVER ---")
    mission = {
        "apiVersion": "intelligence.systems/v0alpha1",
        "kind": "Mission",
        "metadata": {"id": "pilot-sre-incident", "version": 1},
        "objective": {"outcome": "Remediate high memory usage on auth-service-pod-3."},
        "success": {"all": ["memory_usage_normal", "zero_downtime_preserved"]},
        "budget": {"tokens": {"max": 30000}}
    }

    delegation = {
        "id": "del-sre-01",
        "principal": "urn:authority:pagerduty",
        "delegate": "urn:agent:sre-oncall-bot",
        "purpose": "pilot-sre-incident",
        "scope": {
            "allowed_capabilities": ["mcp://k8s/get_logs", "mcp://k8s/restart_pod"],
            "denied_capabilities": ["mcp://k8s/drain_node", "mcp://k8s/delete_deployment"]
        },
        "valid_from": "2026-09-01T00:00:00Z",
        "expires_at": "2026-09-30T00:00:00Z"
    }

    engine = MissionEngine()
    engine.load_mission(mission)
    engine.authorize(delegation)
    engine.start()

    # Step 1: Diagnose
    engine.execute_action("mcp://k8s/get_logs", {"pod": "auth-service-pod-3"}, tokens=250)

    # Step 2: Attempt unauthorized destructive node drain (blocked)
    drain_blocked = False
    try:
        engine.execute_action("mcp://k8s/drain_node", {"node": "worker-pool-1"})
    except PermissionError:
        drain_blocked = True
    assert drain_blocked is True, "Must enforce denied capability"

    # Step 3: Human SRE takes over control
    engine.pause("Operator investigating unusual core dump")
    assert engine.state == "PAUSED"
    engine.resume()
    assert engine.state == "RUNNING"

    # Step 4: Execute benign pod restart
    engine.execute_action("mcp://k8s/restart_pod", {"pod": "auth-service-pod-3"}, tokens=150)
    engine.finish_execution()

    # Step 5: Verifier validates recovery
    engine.record_evidence({
        "id": "ev-sre-1", "mission_id": "pilot-sre-incident",
        "criterion_ref": "memory_usage_normal", "tier": "tier_2_deterministic",
        "verifier": {"type": "test_harness", "identifier": "prometheus-mem-gauge"},
        "result": "SATISFIED", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })
    engine.record_evidence({
        "id": "ev-sre-2", "mission_id": "pilot-sre-incident",
        "criterion_ref": "zero_downtime_preserved", "tier": "tier_2_deterministic",
        "verifier": {"type": "test_harness", "identifier": "uptime-robot"},
        "result": "SATISFIED", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })

    verified = engine.evaluate_verification()
    assert verified is True
    print("[PASS] SRE Pilot: Successfully resolved incident with privilege containment and operator pause/resume.")
    return {"pilot": "sre_incident", "status": "VERIFIED", "events": len(engine.trajectory)}

def test_all_pilots():
    p1 = run_gitops_pilot()
    p2 = run_data_pipeline_pilot()
    p3 = run_sre_incident_pilot()

    summary = [p1, p2, p3]
    out_path = os.path.join(workspace, "data", "results_phase_h_pilots.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n==================================================================")
    print(f"ALL 3 PHASE H ENTERPRISE PILOTS COMPLETED SUCCESSFULLY")
    print(f"Results recorded to: {out_path}")
    print("==================================================================")

if __name__ == "__main__":
    test_all_pilots()
