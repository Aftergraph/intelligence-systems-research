from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/jar-exp-0013-controlled-host.yml"
EXAMPLE = ROOT / "experiments/runtime_acceleration/controlled-host.example.json"
START = ROOT / "experiments/runtime_acceleration/start-controlled-host.ps1"


def test_controlled_host_workflow_is_manual_and_dedicated_self_hosted_only():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "push:" not in text
    assert "pull_request:" not in text
    assert "runs-on: [self-hosted, Windows, X64, aftergraph-jar-exp-0013]" in text
    assert "python -m experiments.runtime_acceleration.controlled_host" in text
    assert "actions/upload-artifact@v4" in text
    assert "deploy" not in text.lower()


def test_controlled_host_example_contains_paths_not_secrets():
    text = EXAMPLE.read_text(encoding="utf-8")
    assert '"experiment_id": "JAR-EXP-0013"' in text
    assert '"hermes_python"' in text
    assert '"hermes_root"' in text
    assert '"workspace"' in text
    assert '"toolrush_repo"' in text
    assert '"toolrush_doctor"' in text
    assert '"toolrush_plugin"' in text
    assert '"obscura_repo"' in text
    assert '"obscura_executable"' in text
    assert '"chromium_executable"' in text
    assert "api_key" not in text.lower()
    assert "token" not in text.lower()
    assert "password" not in text.lower()


def test_local_phase1_execution_requires_explicit_operator_switch():
    text = START.read_text(encoding="utf-8")
    assert "[switch]$RunPhase1" in text
    assert "if (-not $RunPhase1)" in text
    assert '"hermes_root"' in text
    assert '"workspace"' in text
    assert '"toolrush_plugin"' in text
    assert '"chromium_executable"' in text
    assert '"-m", "experiments.runtime_acceleration.phase1_host_run"' in text
    assert '"--plan", $tracePlanPath' in text
    assert '"--probe", $probePath' in text
    assert '"--execution-id", $phase1ExecutionId' in text
