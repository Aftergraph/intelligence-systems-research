from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "experiments" / "runtime_acceleration" / "recover-self-hosted-runner.ps1"

def text():
    return SCRIPT.read_text(encoding="utf-8")

def test_recovery_is_scope_bound_and_fail_closed():
    s = text()
    low = s.lower()
    assert "ExpectedRepositoryUrl" in s
    assert "runner_scope_mismatch" in s
    assert "runner_service_path_mismatch" in s
    assert ".runner" in s
    assert ".service" in s
    assert "refusing to create or replace registration" in low
    assert "refusing to reinstall automatically" in low

def test_recovery_only_restarts_canonical_service():
    s = text()
    assert "Restart-Service -Name $serviceName" in s
    assert "Start-Service -Name $serviceName" in s
    assert "Runner.Listener.exe" in s
    assert "Stop-Process" not in s
    assert "Remove-Item" not in s
    assert "config.cmd" not in s
    assert "svc.cmd install" not in s

def test_recovery_does_not_claim_remote_success_from_local_state():
    s = text()
    assert "GitHub must claim queued ISR jobs" in s
    assert "local listener state alone is not remote assignment proof" in s
    assert "Listening for Jobs" in s
