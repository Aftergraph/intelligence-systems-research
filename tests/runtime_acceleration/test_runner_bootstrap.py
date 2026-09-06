from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / "experiments/runtime_acceleration/bootstrap-self-hosted-runner.ps1"
START_CONTROLLED_HOST = ROOT / "experiments/runtime_acceleration/start-controlled-host.ps1"
CONTROLLED_WORKFLOW = ROOT / ".github/workflows/jar-exp-0013-controlled-host.yml"


def test_runner_bootstrap_is_pinned_verified_and_dedicated():
    text = BOOTSTRAP.read_text(encoding="utf-8")
    assert 'RunnerVersion = "2.337.0"' in text
    assert '1150692afa94e71f872017e254ea55b6eece1eece3fe7e3a6d4c93d0a1b85cfc' in text
    assert "Get-FileHash" in text
    assert "SHA256" in text
    assert "actions-runner-win-x64-$RunnerVersion.zip" in text
    assert "https://github.com/Aftergraph/intelligence-systems-research" in text
    assert "aftergraph-jar-exp-0013" in text
    assert "config.cmd" in text
    assert "--unattended" in text
    assert "svc.cmd" in text
    assert "install" in text
    assert "start" in text


def test_runner_bootstrap_does_not_embed_registration_secret():
    text = BOOTSTRAP.read_text(encoding="utf-8").lower()
    assert "ghp_" not in text
    assert "github_pat_" not in text
    assert "registrationtoken = \"" not in text


def test_one_command_host_start_uses_local_probe_before_optional_dispatch():
    text = START_CONTROLLED_HOST.read_text(encoding="utf-8")
    assert "experiments.runtime_acceleration.controlled_host" in text
    assert "controlled-host-probe.json" in text
    assert "ConvertFrom-Json" in text
    assert 'state -ne "READY"' in text
    assert "[switch]$DispatchWorkflow" in text
    assert "gh workflow run" in text
    assert "jar-exp-0013-controlled-host.yml" in text
    assert "research/jar-exp-0013-runtime-acceleration" in text


def test_ready_host_freezes_unique_trace_measurement_plan():
    text = START_CONTROLLED_HOST.read_text(encoding="utf-8")
    assert "experiments.runtime_acceleration.measurement_plan" in text
    assert "trace_replay.yaml" in text
    assert '"--repetitions", "20"' in text
    assert '"--seed", "130013"' in text
    assert "trace-plan-$planStamp.json" in text
    assert "[DateTime]::UtcNow" in text
    assert "Phase-1 trace plan" in text


def test_one_command_host_start_uses_authenticated_gh_and_short_lived_token():
    text = START_CONTROLLED_HOST.read_text(encoding="utf-8")
    assert "gh auth status" in text
    assert "actions/runners/registration-token" in text
    assert "ConvertTo-SecureString" in text
    assert "bootstrap-self-hosted-runner.ps1" in text
    assert "host_config_path" in text


def test_one_command_host_start_does_not_embed_long_lived_credentials():
    text = START_CONTROLLED_HOST.read_text(encoding="utf-8").lower()
    assert "ghp_" not in text
    assert "github_pat_" not in text
    assert "authorization: bearer" not in text


def test_controlled_workflow_accepts_machine_local_path_without_repo_variable():
    text = CONTROLLED_WORKFLOW.read_text(encoding="utf-8")
    assert "host_config_path:" in text
    assert "workflow_dispatch:" in text
    assert "inputs.host_config_path" in text
    assert "JAR_EXP_0013_HOST_CONFIG" not in text
