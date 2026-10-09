from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from jev_engineering.tools import RepoTools


def test_verify_only_executes_without_shell(tmp_path: Path) -> None:
    tools = RepoTools(tmp_path, command_mode="verify_only")
    seen = {}

    class Result:
        stdout = "ok"
        stderr = ""
        returncode = 0

    def fake_run(argv, **kwargs):
        seen["argv"] = argv
        return Result()

    with patch("jev_engineering.tools.subprocess.run", fake_run):
        result = tools.run_command("python -m pytest -q")
    assert result["exit_code"] == 0
    assert seen["argv"] == ["python", "-m", "pytest", "-q"]
    assert "bash" not in seen["argv"]


def test_verify_only_direct_exec_is_cross_platform_by_construction(tmp_path: Path) -> None:
    tools = RepoTools(tmp_path, command_mode="verify_only")
    with patch("jev_engineering.tools.subprocess.run") as run:
        run.return_value.stdout = ""
        run.return_value.stderr = ""
        run.return_value.returncode = 1
        tools.run_command("python -m pytest -q")
    assert run.call_args.args[0][0] == "python"

from jev_engineering.benchmark import _validate_baseline_verifier
import pytest


def test_pytest_baseline_requires_real_test_failure() -> None:
    assert _validate_baseline_verifier("python -m pytest -q", {"exit_code": 1, "output": "1 failed"}) == 1
    with pytest.raises(RuntimeError, match="infrastructure"):
        _validate_baseline_verifier("python -m pytest -q", {"exit_code": 127, "output": "python: command not found"})
    with pytest.raises(RuntimeError, match="exit 1"):
        _validate_baseline_verifier("python -m pytest -q", {"exit_code": 5, "output": "no tests ran"})