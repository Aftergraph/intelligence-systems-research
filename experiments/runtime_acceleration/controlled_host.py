from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from .host_preflight import check_preflight
from .live_host import CommandResult, build_obscura_serve_argv, git_head, run_argv
from .protocol import load_protocol


DEFAULT_PROTOCOL = Path(__file__).with_name("protocol.yaml")
_REQUIRED_PATHS = (
    "hermes_python",
    "toolrush_repo",
    "toolrush_doctor",
    "obscura_repo",
    "obscura_executable",
)


def capture_preflight_snapshot() -> dict:
    """Capture the live host load needed by the confirmatory contamination gate."""
    try:
        import psutil  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised on the real host workflow
        raise RuntimeError("psutil is required for controlled-host preflight") from exc

    battery = psutil.sensors_battery()
    return {
        "cpu_percent": float(psutil.cpu_percent(interval=1.0)),
        "memory_percent": float(psutil.virtual_memory().percent),
        "on_ac_power": True if battery is None else bool(battery.power_plugged),
        "background_process_count": int(len(psutil.pids())),
        "thermal_state": None,
    }


def _command_summary(result: CommandResult) -> dict:
    """Persist only non-secret command metadata; raw command output is intentionally omitted."""
    return {
        "argv": list(result.argv),
        "returncode": int(result.returncode),
        "duration_ms": float(result.duration_ms),
    }


def _blocked(reasons: list[str], **extra) -> dict:
    return {
        "experiment_id": "JAR-EXP-0013",
        "state": "BLOCKED",
        "reasons": reasons,
        "live_provider_calls": 0,
        "production_mutations": 0,
        **extra,
    }


def probe_host(
    config: dict,
    *,
    runner: Callable[..., CommandResult] = run_argv,
    revision_reader: Callable[[str | Path], str] = git_head,
    snapshot_provider: Callable[[], dict] = capture_preflight_snapshot,
) -> dict:
    """Validate a controlled Windows host without running model/provider workloads."""
    if config.get("experiment_id") != "JAR-EXP-0013":
        return _blocked(["unexpected experiment_id"])

    protocol_path = Path(config.get("protocol_path") or DEFAULT_PROTOCOL)
    try:
        protocol = load_protocol(protocol_path)
    except Exception as exc:
        return _blocked([f"protocol load failed: {exc}"])

    reasons: list[str] = []
    paths: dict[str, Path] = {}
    for field in _REQUIRED_PATHS:
        raw = config.get(field)
        if not raw:
            reasons.append(f"missing config field: {field}")
            continue
        path = Path(str(raw))
        paths[field] = path
        if not path.exists():
            reasons.append(f"path does not exist: {field}={path}")

    pins = {
        "toolrush": str(protocol["pins"]["toolrush"]).lower(),
        "obscura": str(protocol["pins"]["obscura"]).lower(),
    }

    for label, field, expected in (
        ("ToolRush", "toolrush_repo", pins["toolrush"]),
        ("Obscura", "obscura_repo", pins["obscura"]),
    ):
        path = paths.get(field)
        if path is None or not path.exists():
            continue
        try:
            actual = str(revision_reader(path)).strip().lower()
        except Exception as exc:
            reasons.append(f"{label} revision check failed: {exc}")
            continue
        if actual != expected:
            reasons.append(f"{label} revision mismatch: expected {expected}, got {actual}")

    toolrush_doctor: dict | None = None
    hermes_python = paths.get("hermes_python")
    doctor = paths.get("toolrush_doctor")
    if hermes_python and doctor and hermes_python.exists() and doctor.exists():
        try:
            doctor_result = runner(
                [str(hermes_python), str(doctor), "--smoke"],
                timeout_s=120,
            )
            toolrush_doctor = _command_summary(doctor_result)
            if doctor_result.returncode != 0:
                reasons.append("ToolRush doctor smoke failed")
        except Exception as exc:
            reasons.append(f"ToolRush doctor smoke failed: {exc}")

    obscura_version: dict | None = None
    obscura_executable = paths.get("obscura_executable")
    if obscura_executable and obscura_executable.exists():
        try:
            version_result = runner([str(obscura_executable), "--version"], timeout_s=30)
            obscura_version = _command_summary(version_result)
            if version_result.returncode != 0:
                reasons.append("Obscura version probe failed")
        except Exception as exc:
            reasons.append(f"Obscura version probe failed: {exc}")

    limits = config.get("preflight_limits")
    if not isinstance(limits, dict):
        reasons.append("missing preflight_limits")
        preflight = {"clean": False, "reasons": ["missing_preflight_limits"]}
        snapshot = {}
    else:
        try:
            snapshot = dict(snapshot_provider())
            preflight = check_preflight(snapshot, limits)
        except Exception as exc:
            reasons.append(f"preflight capture failed: {exc}")
            snapshot = {}
            preflight = {"clean": False, "reasons": ["preflight_capture_failed"]}

    try:
        obscura_serve_argv = build_obscura_serve_argv(
            config.get("obscura_executable", "obscura"),
            port=int(config.get("obscura_port", 9222)),
        )
    except Exception as exc:
        reasons.append(f"invalid Obscura serve configuration: {exc}")
        obscura_serve_argv = []

    if reasons:
        state = "BLOCKED"
    elif not preflight.get("clean"):
        state = "CONTAMINATED"
    else:
        state = "READY"

    return {
        "experiment_id": "JAR-EXP-0013",
        "state": state,
        "reasons": reasons,
        "pins": pins,
        "preflight": dict(preflight),
        "snapshot": snapshot,
        "toolrush_doctor": toolrush_doctor,
        "obscura_version": obscura_version,
        "obscura_serve_argv": obscura_serve_argv,
        "live_provider_calls": 0,
        "production_mutations": 0,
    }


def load_config(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("controlled-host config must be a JSON object")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="JAR-EXP-0013 controlled-host probe")
    parser.add_argument("--config", required=True, help="Path to machine-local JSON config")
    parser.add_argument("--output", help="Optional JSON output path for artifact upload")
    args = parser.parse_args(argv)

    result = probe_host(load_config(args.config))
    serialized = json.dumps(result, indent=2, sort_keys=True)
    print(serialized)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized + "\n", encoding="utf-8")
    return 0 if result["state"] == "READY" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
