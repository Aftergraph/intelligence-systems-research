from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "experiments/runtime_acceleration/start-hermes-toolrush.ps1"


def test_launcher_has_fail_safe_runtime_controls():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "AFTERGRAPH_TOOLRUSH_DISABLED" in text
    assert "TOOLRUSH_FASTLANE" in text
    assert "TOOLRUSH_SEARCH" in text
    assert "TOOLRUSH_PERSIST" in text
    assert "doctor.py" in text or "ToolRushDoctor" in text
    assert "Get-FileHash" in text
    assert "git -C" in text
    assert "runtime-status" in text
    assert "selected_runtime" in text
    assert "fallback_reason" in text
    assert "& $HermesExe @HermesArgs" in text


def test_launcher_never_enables_obscura():
    text = LAUNCHER.read_text(encoding="utf-8").lower()
    assert "obscura" not in text
