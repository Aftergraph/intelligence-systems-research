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


def test_one_command_host_start_defaults_remote_dispatch_to_canonical_main():
    text = START_CONTROLLED_HOST.read_text(encoding="utf-8")
    assert '[string]$Branch = "main"' in text
    assert 'research/jar-exp-0013-runtime-acceleration' not in text


def test_ready_host_freezes_unique_trace_measurement_plan():
    text = START_CONTROLLED_HOST.read_text(encoding="utf-8")
    assert "experiments.runtime_acceleration.measurement_plan" in text
    assert "trace_replay.yaml" in text
    assert '"--repetitions", "20"' in text
    assert '"--seed", "130013"' in text
    assert "trace-plan-$planStamp.json" in text
    assert "[DateTime]::UtcNow" in text
    assert "Phase-1 trace plan" in text


def test_phase1_execution_automatically_writes_trace_analysis_outputs():
    text = START_CONTROLLED_HOST.read_text(encoding="utf-8")
    assert "experiments.runtime_acceleration.phase1_analysis" in text
    assert "summary.json" in text
    assert "phase1-analysis.json" in text
    assert "phase1-analysis.md" in text
    assert '"--json-output"' in text
    assert '"--markdown-output"' in text
    assert "Promotion gates remain INCONCLUSIVE after Phase-1 trace analysis" in text


def test_phase1_diagnostic_analysis_runs_before_nonclean_exit():
    text = START_CONTROLLED_HOST.read_text(encoding="utf-8")
    assert "$phase1RunExit = $LASTEXITCODE" in text
    run_index = text.index("experiments.runtime_acceleration.phase1_host_run")
    analysis_index = text.index("experiments.runtime_acceleration.phase1_analysis")
    exit_index = text.index("if ($phase1RunExit -ne 0)")
    assert run_index < analysis_index < exit_index
    assert "Diagnostic Phase-1 analysis was retained" in text


def test_phase2_execution_freezes_plan_and_runs_analysis_before_nonclean_exit():
    text = START_CONTROLLED_HOST.read_text(encoding="utf-8")
    assert "[switch]$RunPhase2" in text
    assert "experiments.runtime_acceleration.phase2_tool_microbench" in text
    assert "tool_microbench.yaml" in text
    assert "phase2-plan-$phase2PlanStamp.json" in text
    assert "experiments.runtime_acceleration.phase2_host_run" in text
    assert "experiments.runtime_acceleration.phase2_analysis" in text
    assert "phase2-analysis.json" in text
    assert "phase2-analysis.md" in text
    assert "$phase2RunExit = $LASTEXITCODE" in text
    run_index = text.index("experiments.runtime_acceleration.phase2_host_run")
    analysis_index = text.index("experiments.runtime_acceleration.phase2_analysis")
    exit_index = text.index("if ($phase2RunExit -ne 0)")
    assert run_index < analysis_index < exit_index
    assert "Promotion gates remain INCONCLUSIVE after Phase-2 tool analysis" in text


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
