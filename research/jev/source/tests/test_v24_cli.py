from __future__ import annotations

import json
from typer.testing import CliRunner

from jev_engineering.cli import app


def test_v24_demo_cli():
    result = CliRunner().invoke(app, ["v24-demo"])
    assert result.exit_code == 0, result.output
    assert '"relay_generation_monotonic": true' in result.output
    assert '"journal_checkpoint_complete": true' in result.output
    assert '"campaign_state": "promoted"' in result.output
    assert '"live_provider_measurement": false' in result.output


def test_physical_pair_template_cli(tmp_path):
    out = tmp_path / "pair.json"
    result = CliRunner().invoke(app, ["physical-pair-template", "--output", str(out)])
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text())
    assert payload["version"] == 1
    assert len(payload["nodes"]) == 2
