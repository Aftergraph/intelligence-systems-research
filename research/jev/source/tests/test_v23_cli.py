from typer.testing import CliRunner

from jev_engineering.cli import app


def test_v23_demo_cli():
    result = CliRunner().invoke(app, ["v23-demo"])
    assert result.exit_code == 0, result.output
    assert '"node_connection_direction": "worker-outbound-to-relay"' in result.output
    assert '"node_inbound_listener": false' in result.output
    assert '"remote_verifier_subprocess": "PASS"' in result.output
    assert '"receipt_stream_same_head": true' in result.output
    assert '"physical_multi_machine_executed": false' in result.output
