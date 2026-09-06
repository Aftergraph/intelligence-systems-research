from experiments.runtime_acceleration.dry_run import NEGATIVE_CONTROLS, run_dry_run


def test_dry_run_proves_harness_ready_without_live_provider(tmp_path):
    result = run_dry_run(tmp_path)
    assert result["live_provider_calls"] == 0
    assert result["production_mutations"] == 0
    assert result["verdict"] == "READY_FOR_CONTROLLED_HOST_RUN"
    assert result["fixture_server"] == "PASS"
    assert result["trace_replay"] == "PASS"
    assert result["evidence_contract"] == "PASS"
    assert len(NEGATIVE_CONTROLS) == 6
