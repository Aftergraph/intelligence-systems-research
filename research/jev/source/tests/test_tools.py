from __future__ import annotations

import pathlib

import pytest

from jev_engineering.tools import RepoTools, ToolPolicyError


def test_repo_tools_prevent_path_escape(tmp_path: pathlib.Path) -> None:
    tools = RepoTools(tmp_path)
    with pytest.raises(ToolPolicyError):
        tools.read_file("../secret.txt")


def test_read_write_search_and_diff_like_behavior(tmp_path: pathlib.Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    tools = RepoTools(tmp_path)
    assert "x = 1" in tools.read_file("a.py")["content"]
    tools.write_file("a.py", "x = 2\n")
    out = tools.search_text("x = 2")
    assert out["matches"][0]["path"] == "a.py"


def test_hard_deny_rejects_catastrophic_commands(tmp_path: pathlib.Path) -> None:
    tools = RepoTools(tmp_path)
    with pytest.raises(ToolPolicyError):
        tools.run_command("rm -rf /", safety_action="allow")


def test_verify_only_rejects_shell_chaining_even_after_allowlisted_prefix(tmp_path) -> None:
    tools = RepoTools(tmp_path, command_mode="verify_only")
    with pytest.raises(ToolPolicyError):
        tools.preflight("run_command", {"command": "python -m pytest -q; touch /tmp/escaped"})


def test_verify_only_rejects_parent_or_absolute_path_arguments(tmp_path) -> None:
    tools = RepoTools(tmp_path, command_mode="verify_only")
    with pytest.raises(ToolPolicyError):
        tools.preflight("run_command", {"command": "python -m pytest ../../outside"})
    with pytest.raises(ToolPolicyError):
        tools.preflight("run_command", {"command": "python -m pytest /tmp/outside"})
