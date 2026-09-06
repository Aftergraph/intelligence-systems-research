from __future__ import annotations

from pathlib import Path

from experiments.runtime_acceleration.controlled_host import probe_host
from experiments.runtime_acceleration.live_host import CommandResult

TOOLRUSH_PIN = "4ecd8810fdc9e6e0c64af3d532f876d06f6a278e"
OBSCURA_PIN = "a1e09de68c7617b8079fbb1661b0548c501971c1"


def _config(tmp_path: Path) -> dict:
    toolrush_repo = tmp_path / "toolrush"
    obscura_repo = tmp_path / "obscura"
    toolrush_repo.mkdir()
    obscura_repo.mkdir()
    hermes_python = tmp_path / "python.exe"
    doctor = tmp_path / "doctor.py"
    obscura_exe = tmp_path / "obscura.exe"
    for path in (hermes_python, doctor, obscura_exe):
        path.write_text("fixture", encoding="utf-8")
    return {
        "experiment_id": "JAR-EXP-0013",
        "hermes_python": str(hermes_python),
        "toolrush_repo": str(toolrush_repo),
        "toolrush_doctor": str(doctor),
        "obscura_repo": str(obscura_repo),
        "obscura_executable": str(obscura_exe),
        "obscura_port": 9222,
    }


def _runner(argv, **kwargs):
    text = "toolrush smoke ok" if "--smoke" in argv else "obscura 0.1.0"
    return CommandResult(tuple(str(x) for x in argv), 0, text, "", 1.25)


def _clean_snapshot():
    return {
        "cpu_percent": 5.0,
        "memory_percent": 30.0,
        "on_ac_power": True,
        "background_process_count": 42,
        "thermal_state": None,
    }


def _revisions(config: dict) -> dict:
    return {
        str(Path(config["toolrush_repo"])): TOOLRUSH_PIN,
        str(Path(config["obscura_repo"])): OBSCURA_PIN,
    }


def test_probe_host_ready_requires_exact_pins_and_protocol_preflight(tmp_path):
    config = _config(tmp_path)
    revisions = _revisions(config)
    result = probe_host(
        config,
        runner=_runner,
        revision_reader=lambda path: revisions[str(Path(path))],
        snapshot_provider=_clean_snapshot,
    )
    assert result["state"] == "READY"
    assert result["pins"]["toolrush"] == TOOLRUSH_PIN
    assert result["pins"]["obscura"] == OBSCURA_PIN
    assert result["preflight_limits"] == {
        "cpu_percent_max": 20.0,
        "memory_percent_max": 80.0,
        "require_ac_power": True,
    }
    assert result["preflight"]["clean"] is True
    assert result["toolrush_doctor"]["returncode"] == 0
    assert result["obscura_version"]["returncode"] == 0
    assert result["obscura_serve_argv"][-2:] == ["--host", "127.0.0.1"]
    assert result["live_provider_calls"] == 0
    assert result["production_mutations"] == 0


def test_probe_host_blocks_revision_drift(tmp_path):
    config = _config(tmp_path)
    result = probe_host(
        config,
        runner=_runner,
        revision_reader=lambda path: "0" * 40,
        snapshot_provider=_clean_snapshot,
    )
    assert result["state"] == "BLOCKED"
    assert any("revision mismatch" in reason for reason in result["reasons"])


def test_probe_host_marks_dirty_machine_contaminated(tmp_path):
    config = _config(tmp_path)
    revisions = _revisions(config)
    result = probe_host(
        config,
        runner=_runner,
        revision_reader=lambda path: revisions[str(Path(path))],
        snapshot_provider=lambda: {
            "cpu_percent": 55.0,
            "memory_percent": 30.0,
            "on_ac_power": True,
        },
    )
    assert result["state"] == "CONTAMINATED"
    assert result["preflight"]["reasons"] == ["cpu_percent"]


def test_probe_host_rejects_host_override_that_weakens_frozen_preflight(tmp_path):
    config = _config(tmp_path)
    config["preflight_limits"] = {
        "cpu_percent_max": 99.0,
        "memory_percent_max": 99.0,
        "require_ac_power": False,
    }
    revisions = _revisions(config)
    result = probe_host(
        config,
        runner=_runner,
        revision_reader=lambda path: revisions[str(Path(path))],
        snapshot_provider=_clean_snapshot,
    )
    assert result["state"] == "BLOCKED"
    assert "preflight_limits override differs from frozen protocol" in result["reasons"]
