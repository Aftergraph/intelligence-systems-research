from __future__ import annotations

from typer.testing import CliRunner

from jev_engineering.cli import app


def test_v25_demo_cli():
    result = CliRunner().invoke(app, ["v25-demo"])
    assert result.exit_code == 0, result.output
    assert '"holdout_only_promotion": true' in result.output
    assert '"evidence_bundle_verified": true' in result.output
    assert '"target_attainable_by_control_plane_only": false' in result.output
    assert '"live_provider_measurement": false' in result.output


def test_v25_report_rejects_placeholder_pricing(tmp_path):
    results = tmp_path / "results.jsonl"
    results.write_text("", encoding="utf-8")
    pricing = tmp_path / "pricing.json"
    pricing.write_text('{"replace_before_use":true,"generator":{"input_per_million":0,"output_per_million":0},"decision_by_condition":{"a":{"input_per_million":0,"output_per_million":0}},"frontier_decision_conditions":[]}\n', encoding="utf-8")
    result = CliRunner().invoke(app, [
        "campaign-report-v25", str(results), "--pricing", str(pricing),
        "--incumbent", "a", "--candidate", "b",
        "--shadow-pairs", "1", "--experiment-pairs", "1", "--holdout-pairs", "1",
    ])
    assert result.exit_code != 0
    assert "placeholder" in str(result.exception).lower()


def test_live_campaign_v25_validates_pricing_before_provider_execution(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("name: would-not-run\n", encoding="utf-8")
    pricing = tmp_path / "pricing.json"
    pricing.write_text('{"replace_before_use":true}\n', encoding="utf-8")
    called = {"run": False}

    def forbidden(*args, **kwargs):
        called["run"] = True
        raise AssertionError("provider benchmark must not start")

    monkeypatch.setattr("jev_engineering.cli.run_manifest", forbidden)
    result = CliRunner().invoke(app, [
        "live-campaign-v25", str(manifest), "--pricing", str(pricing),
        "--incumbent", "a", "--candidate", "b",
    ])
    assert result.exit_code != 0
    assert called["run"] is False
    assert "placeholder" in str(result.exception).lower()
