from pathlib import Path

import jev_engineering as jev
from typer.testing import CliRunner

from jev_engineering.cli import app


def test_v212_public_api_exports():
    for name in (
        "MultiAgentOrchestrator", "MultiAgentPlan", "MultiAgentRunResult", "SubagentSpec",
        "SubagentTask", "SubagentOutcome", "SubagentStatus", "JoinMode", "JoinPolicy",
    ):
        assert hasattr(jev, name), name


def test_v212_version():
    from packaging.version import Version
    assert Version(jev.__version__) >= Version("2.12.0")


def test_v212_schemas_exist():
    root = Path(jev.__file__).parent / "schemas"
    assert (root / "multi-agent-plan.v1.schema.json").is_file()
    assert (root / "multi-agent-run.v1.schema.json").is_file()


def test_v212_demo_is_claim_safe():
    result = CliRunner().invoke(app, ["v212-demo"])
    assert result.exit_code == 0, result.output
    assert '"accepted": true' in result.output
    assert '"provider_calls": 0' in result.output
    assert '"live_provider_measurement": false' in result.output