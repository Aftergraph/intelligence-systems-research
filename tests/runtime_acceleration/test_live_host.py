from __future__ import annotations

import sys
from pathlib import Path

import pytest

from experiments.runtime_acceleration.live_host import (
    RevisionMismatch,
    build_obscura_serve_argv,
    git_head,
    require_revision,
    run_argv,
    sanitize_environment,
)

ROOT = Path(__file__).resolve().parents[2]


def test_run_argv_executes_without_shell_and_records_duration():
    result = run_argv([sys.executable, "-c", "print('bridge-ok')"], cwd=ROOT)
    assert result.returncode == 0
    assert result.stdout.strip() == "bridge-ok"
    assert result.stderr == ""
    assert result.duration_ms >= 0.0
    assert result.argv[0] == sys.executable


def test_run_argv_rejects_string_command_to_prevent_shell_parsing():
    with pytest.raises(TypeError, match="argv must be a sequence"):
        run_argv("echo unsafe")


def test_sanitize_environment_redacts_secret_like_values():
    sanitized = sanitize_environment(
        {
            "PATH": "C:/safe/bin",
            "OPENAI_API_KEY": "should-not-leak",
            "HERMES_TOKEN": "should-not-leak-either",
            "NORMAL_FLAG": "visible",
        }
    )
    assert sanitized["PATH"] == "C:/safe/bin"
    assert sanitized["NORMAL_FLAG"] == "visible"
    assert sanitized["OPENAI_API_KEY"] == "<redacted>"
    assert sanitized["HERMES_TOKEN"] == "<redacted>"
    assert "should-not-leak" not in repr(sanitized)


def test_git_head_reads_checkout_revision_and_require_revision_fails_closed():
    actual = git_head(ROOT)
    assert len(actual) == 40
    assert all(char in "0123456789abcdef" for char in actual)
    assert require_revision(ROOT, actual, "ISR checkout") == actual
    with pytest.raises(RevisionMismatch, match="ISR checkout revision mismatch"):
        require_revision(ROOT, "0" * 40, "ISR checkout")


def test_obscura_serve_command_is_loopback_cdp_server():
    assert build_obscura_serve_argv(Path("C:/tools/obscura.exe"), port=9333) == [
        "C:/tools/obscura.exe",
        "serve",
        "--port",
        "9333",
        "--host",
        "127.0.0.1",
    ]
