from experiments.study015.preflight import run_preflight


def test_g15_preflight_builds_every_technical_gate_but_does_not_authorize_execution():
    result = run_preflight()
    assert result["status"] == "TECHNICAL_BUILD_PASS"
    assert result["confirmatory_execution_authorized"] is False
    assert result["checks"]["G15-9_owner_gate_pending"] is True
    for key, value in result["checks"].items():
        assert value is True, key
