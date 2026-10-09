from typer.testing import CliRunner
from jev_engineering.cli import app

def test_v27_demo_truth_boundary_and_paths():
    r=CliRunner().invoke(app,["v27-demo"])
    assert r.exit_code == 0, r.output
    assert 'v2.7-empirical-efficiency-execution-engine' in r.output
    assert '"frontier_calls": 0' in r.output
    assert 'live_provider_measurement' in r.output
    assert 'false' in r.output.lower()
