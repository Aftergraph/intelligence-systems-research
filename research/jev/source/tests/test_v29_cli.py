from typer.testing import CliRunner
from jev_engineering.cli import app


def test_v29_demo_is_cryptographically_verified_but_claim_safe():
    result = CliRunner().invoke(app, ["v29-demo"])
    assert result.exit_code == 0, result.output
    assert "v2.9-authenticated-live-ab-evidence-gate" in result.output
    assert '"receipts_verify": true' in result.output.lower()
    assert '"live_provider_measurement": false' in result.output.lower()
    assert '"authenticated_live_ab_executed": false' in result.output.lower()
