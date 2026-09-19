from experiments.verge_traceglass.contract import audit_record


def compatible_record():
    return {
        "run_id": "run-1",
        "workload_id": "workload-1",
        "confidence_threshold": 0.9,
        "verification_depth": 4,
        "retry_ceiling": 2,
        "min_confidence": 0.85,
        "min_verification": 3,
        "min_retries": 1,
        "verified_success": 1,
        "false_completion": 0,
        "unauthorized_actions": 0,
        "evidence_integrity_failures": 0,
        "cost": 1.2,
        "latency": 2.3,
        "human_interventions": 0,
        "source_artifact": "evidence/run-1.json",
        "source_hash": "abc123",
    }


def test_complete_non_simulated_record_is_admissible():
    result = audit_record("trace", "LIVE_EXECUTION", compatible_record())
    assert result.admissible is True
    assert result.evidence_class == "TRACE_COMPATIBLE"
    assert result.missing_fields == ()


def test_missing_policy_margin_fields_fail_closed():
    record = compatible_record()
    del record["confidence_threshold"]
    del record["verification_depth"]
    result = audit_record("trace", "LIVE_EXECUTION", record)
    assert result.admissible is False
    assert "confidence_threshold" in result.missing_fields
    assert "verification_depth" in result.missing_fields


def test_fixture_and_simulation_classes_are_never_promoted():
    for evidence_class in ("SIMULATION_ONLY", "FIXTURE_ONLY", "INFRASTRUCTURE_ONLY"):
        result = audit_record("trace", evidence_class, compatible_record())
        assert result.admissible is False
        assert result.evidence_class == evidence_class


def test_live_provider_record_still_requires_pre_action_policy_fields():
    record = compatible_record()
    for field in ("confidence_threshold", "verification_depth", "retry_ceiling"):
        del record[field]
    result = audit_record("study011", "PROVIDER_LIVE_PARTIAL", record)
    assert result.admissible is False
    assert set(result.missing_fields) >= {
        "confidence_threshold",
        "verification_depth",
        "retry_ceiling",
    }
