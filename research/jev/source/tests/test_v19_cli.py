from typer.testing import CliRunner

from jev_engineering.cli import app


def test_transport_demo_cli():
    result = CliRunner().invoke(app, ["transport-demo"])
    assert result.exit_code == 0, result.output
    assert '"proof_accepted": true' in result.output
    assert '"shell_authority_exposed": false' in result.output
    assert '"network_socket_executed": false' in result.output
