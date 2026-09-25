from typer.testing import CliRunner

from jev_engineering.cli import app


def test_distributed_demo_runs_end_to_end() -> None:
    result = CliRunner().invoke(app, ["distributed-demo"])
    assert result.exit_code == 0, result.output
    assert 'offline-v1.7-distributed-verified-intelligence-demo' in result.output
    assert 'committed' in result.output
    assert 'secondary' in result.output
    assert 'promoted' in result.output
    assert 'true' in result.output.lower()
