import hashlib
import json
import time

# ponytail: 25 standardized live benchmark workloads across 5 operational domains.
# Supports nominal and failure-injected execution with deterministic ground-truth verification.

def get_live_study_workloads():
    workloads = []

    # Domain 1: Software Engineering (SWE)
    swe_tasks = [
        ("SWE-01", "Fix off-by-one error in pagination parser", "slice_range_end_inclusive", True, "FAIL-NONE"),
        ("SWE-02", "Resolve race condition in concurrent lock manager", "thread_safe_double_check", True, "FAIL-TOOL"),
        ("SWE-03", "Remediate SQL injection vulnerability in search query", "parameterized_query_binding", True, "FAIL-NONE"),
        ("SWE-04", "Update deprecated cryptography cipher to AES-GCM", "aes_256_gcm_auth_tag", True, "FAIL-HALLUC"),
        ("SWE-05", "Fix buffer overflow boundary in protocol frame reader", "bounded_frame_length_check", True, "FAIL-VERIF")
    ]
    for tid, title, criteria, gt_pass, f_mode in swe_tasks:
        workloads.append({
            "id": tid,
            "domain": "software_engineering",
            "title": title,
            "prompt": f"You are an autonomous software engineer. Task: {title}. Ensure {criteria} is satisfied and regression tests pass.",
            "criteria_id": criteria,
            "ground_truth_pass": gt_pass,
            "failure_injection": f_mode,
            "budget": {"max_tokens": 8000, "max_cost_usd": 0.05, "max_duration_sec": 30},
            "mission": {
                "version": "intelligence-system/v0alpha1",
                "metadata": {"id": f"msn-{tid.lower()}", "title": title, "owner": "Jonas Abde"},
                "intent": {"goal": title, "rationale": "Live empirical validation"},
                "success": {"all": [criteria]},
                "constraints": {"deterministic_verifier": True}
            },
            "delegation": {
                "token_id": f"del-{tid.lower()}",
                "delegator": "AssurancePrincipal",
                "delegatee": "InHouseAgent",
                "capabilities": ["fs.read", "fs.write", "test.execute"],
                "purpose": f"Resolve {tid}",
                "valid_until": "2026-12-31T23:59:59Z"
            }
        })

    # Domain 2: DevOps & SRE (SRE)
    sre_tasks = [
        ("SRE-01", "Diagnose and remediate CrashLoopBackOff on auth pod", "pod_restarted_healthy_status", True, "FAIL-NONE"),
        ("SRE-02", "Rollback failed canary release upon Prometheus latency spike", "traffic_routed_to_stable_baseline", True, "FAIL-STALE"),
        ("SRE-03", "Rotate expired TLS certificates on ingress gateway", "cert_valid_and_handshake_200", True, "FAIL-REVOKE"),
        ("SRE-04", "Apply zero-downtime database migration schema patch", "schema_version_current_and_unlocked", True, "FAIL-NONE"),
        ("SRE-05", "Resolve memory leak by cycling leaked worker processes", "worker_rss_below_threshold", True, "FAIL-PARTIAL")
    ]
    for tid, title, criteria, gt_pass, f_mode in sre_tasks:
        workloads.append({
            "id": tid,
            "domain": "devops_sre",
            "title": title,
            "prompt": f"You are an SRE incident responder. Task: {title}. Confirm {criteria} before marking resolved.",
            "criteria_id": criteria,
            "ground_truth_pass": gt_pass,
            "failure_injection": f_mode,
            "budget": {"max_tokens": 10000, "max_cost_usd": 0.08, "max_duration_sec": 45},
            "mission": {
                "version": "intelligence-system/v0alpha1",
                "metadata": {"id": f"msn-{tid.lower()}", "title": title, "owner": "Jonas Abde"},
                "intent": {"goal": title, "rationale": "Live SRE validation"},
                "success": {"all": [criteria]},
                "constraints": {"deterministic_verifier": True}
            },
            "delegation": {
                "token_id": f"del-{tid.lower()}",
                "delegator": "AssurancePrincipal",
                "delegatee": "InHouseAgent",
                "capabilities": ["k8s.get", "k8s.restart", "metrics.probe"],
                "purpose": f"Resolve {tid}",
                "valid_until": "2026-12-31T23:59:59Z"
            }
        })

    # Domain 3: Data Engineering (DE)
    de_tasks = [
        ("DE-01", "Validate and sanitize multi-source CSV financial ingest", "zero_null_records_and_types_enforced", True, "FAIL-NONE"),
        ("DE-02", "Reconcile ledger discrepancies between Postgres and ClickHouse", "ledger_delta_exactly_zero", True, "FAIL-BUDGET"),
        ("DE-03", "Deduplicate customer event stream using sliding window", "idempotent_event_ids_unique", True, "FAIL-NONE"),
        ("DE-04", "Transform unnested JSON payloads into DuckDB parquet format", "parquet_schema_conforms_to_spec", True, "FAIL-PRESSURE"),
        ("DE-05", "Recover corrupted partition files from backup mirror", "partition_crc32_checksum_verified", True, "FAIL-REC-EXH")
    ]
    for tid, title, criteria, gt_pass, f_mode in de_tasks:
        workloads.append({
            "id": tid,
            "domain": "data_engineering",
            "title": title,
            "prompt": f"You are a Data Engineer. Task: {title}. Criterion: {criteria}.",
            "criteria_id": criteria,
            "ground_truth_pass": gt_pass,
            "failure_injection": f_mode,
            "budget": {"max_tokens": 12000, "max_cost_usd": 0.06, "max_duration_sec": 40},
            "mission": {
                "version": "intelligence-system/v0alpha1",
                "metadata": {"id": f"msn-{tid.lower()}", "title": title, "owner": "Jonas Abde"},
                "intent": {"goal": title, "rationale": "Live Data Eng validation"},
                "success": {"all": [criteria]},
                "constraints": {"deterministic_verifier": True}
            },
            "delegation": {
                "token_id": f"del-{tid.lower()}",
                "delegator": "AssurancePrincipal",
                "delegatee": "InHouseAgent",
                "capabilities": ["db.query", "db.transform", "fs.read"],
                "purpose": f"Resolve {tid}",
                "valid_until": "2026-12-31T23:59:59Z"
            }
        })

    # Domain 4: Research & Information Synthesis (RES)
    res_tasks = [
        ("RES-01", "Synthesize IEEE and ISO compliance requirements for autonomous agents", "cross_standard_mapping_complete", True, "FAIL-NONE"),
        ("RES-02", "Extract factual claims and compute verifiable provenance chains", "every_claim_has_primary_doi", True, "FAIL-TOOL"),
        ("RES-03", "Audit cryptographic protocol against NIST post-quantum guidance", "quantum_resistant_primitives_verified", True, "FAIL-NONE"),
        ("RES-04", "Identify and resolve contradictory claims across research papers", "conflict_resolution_matrix_produced", True, "FAIL-HALLUC"),
        ("RES-05", "Summarize multi-tier latency overhead under varying concurrency", "p50_p90_p99_tabulated_and_graphed", True, "FAIL-NONE")
    ]
    for tid, title, criteria, gt_pass, f_mode in res_tasks:
        workloads.append({
            "id": tid,
            "domain": "research_synthesis",
            "title": title,
            "prompt": f"You are a Research Systems Analyst. Task: {title}. Verify that {criteria} is satisfied.",
            "criteria_id": criteria,
            "ground_truth_pass": gt_pass,
            "failure_injection": f_mode,
            "budget": {"max_tokens": 15000, "max_cost_usd": 0.10, "max_duration_sec": 60},
            "mission": {
                "version": "intelligence-system/v0alpha1",
                "metadata": {"id": f"msn-{tid.lower()}", "title": title, "owner": "Jonas Abde"},
                "intent": {"goal": title, "rationale": "Live Research validation"},
                "success": {"all": [criteria]},
                "constraints": {"deterministic_verifier": True}
            },
            "delegation": {
                "token_id": f"del-{tid.lower()}",
                "delegator": "AssurancePrincipal",
                "delegatee": "InHouseAgent",
                "capabilities": ["web.search", "doc.read", "report.write"],
                "purpose": f"Resolve {tid}",
                "valid_until": "2026-12-31T23:59:59Z"
            }
        })

    # Domain 5: Agent Operations & Tool Orchestration (OPS)
    ops_tasks = [
        ("OPS-01", "Dispatch multi-turn capability pipeline with temporal token refresh", "all_pipeline_steps_receipted", True, "FAIL-NONE"),
        ("OPS-02", "Safely isolate compromised worker subagent upon anomaly detection", "subagent_authority_revoked_and_killed", True, "FAIL-REVOKE"),
        ("OPS-03", "Execute atomic 2-phase budget reservation across 4 concurrent tasks", "budget_never_exceeded_and_committed", True, "FAIL-NONE"),
        ("OPS-04", "Reconcile uncommitted remote side effect after simulated crash", "side_effect_idempotency_preserved", True, "FAIL-STALE"),
        ("OPS-05", "Progressive disclosure contract injection under tight context window", "pinned_constraints_zero_loss", True, "FAIL-PRESSURE")
    ]
    for tid, title, criteria, gt_pass, f_mode in ops_tasks:
        workloads.append({
            "id": tid,
            "domain": "agent_operations",
            "title": title,
            "prompt": f"You are an Agent Operations Controller. Task: {title}. Ensure {criteria}.",
            "criteria_id": criteria,
            "ground_truth_pass": gt_pass,
            "failure_injection": f_mode,
            "budget": {"max_tokens": 10000, "max_cost_usd": 0.05, "max_duration_sec": 30},
            "mission": {
                "version": "intelligence-system/v0alpha1",
                "metadata": {"id": f"msn-{tid.lower()}", "title": title, "owner": "Jonas Abde"},
                "intent": {"goal": title, "rationale": "Live Ops validation"},
                "success": {"all": [criteria]},
                "constraints": {"deterministic_verifier": True}
            },
            "delegation": {
                "token_id": f"del-{tid.lower()}",
                "delegator": "AssurancePrincipal",
                "delegatee": "InHouseAgent",
                "capabilities": ["agent.spawn", "agent.kill", "token.refresh"],
                "purpose": f"Resolve {tid}",
                "valid_until": "2026-12-31T23:59:59Z"
            }
        })

    return workloads
