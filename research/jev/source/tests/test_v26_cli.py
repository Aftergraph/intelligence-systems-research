from __future__ import annotations

import json
from typer.testing import CliRunner

from jev_engineering.cli import app


def test_v26_demo_cli():
    result = CliRunner().invoke(app, ["v26-demo"])
    assert result.exit_code == 0, result.output
    assert '"modeled_10x_attainable": true' in result.output
    assert '"observed_evidence_10x_attainable": false' in result.output
    assert '"live_provider_measurement": false' in result.output
    assert '"verified_early_exit_uses_frontier": false' in result.output


def test_efficiency_plan_v26_cli(tmp_path):
    profile = tmp_path / "profile.json"
    levers = tmp_path / "levers.json"
    profile.write_text(json.dumps({"profile_id": "p", "categories": {"x": 100}}), encoding="utf-8")
    levers.write_text(json.dumps([
        {"lever_id": "half", "reductions": {"x": 0.5}, "evidence_level": "observed"}
    ]), encoding="utf-8")
    result = CliRunner().invoke(app, [
        "efficiency-plan-v26", str(profile), "--levers", str(levers),
        "--target-ratio", "2", "--min-evidence", "observed",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["plan"]["target_met"] is True
    assert payload["plan"]["projected_ratio"] == 2.0
