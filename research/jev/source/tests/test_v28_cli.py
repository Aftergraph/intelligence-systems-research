from typer.testing import CliRunner
from jev_engineering.cli import app


def test_v28_demo_is_claim_safe():
    result = CliRunner().invoke(app, ["v28-demo"])
    assert result.exit_code == 0, result.output
    assert "v2.8-paired-provider-holdout-execution" in result.output
    assert '"live_provider_measurement": false' in result.output.lower()
    assert '"evidence_scope": "holdout-only"' in result.output
