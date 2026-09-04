import os
import subprocess
import sys
import pytest

# Ensure workspace root is in sys.path
base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
cli_path = os.path.join(workspace, "cli", "mission_cli.py")

# ponytail: Automated test suite for mission CLI tooling.

def run_cli(*args):
    cmd = [sys.executable, cli_path] + list(args)
    res = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True)
    return res

def test_cli_lint_valid_mission():
    mission_file = os.path.join(workspace, "examples", "mission.release.yaml")
    res = run_cli("lint", mission_file)
    assert res.returncode == 0
    assert "is valid against schema" in res.stdout

def test_cli_lint_valid_manifest():
    manifest_file = os.path.join(workspace, "examples", "INTELLIGENCE.yaml")
    res = run_cli("lint", manifest_file)
    assert res.returncode == 0
    assert "is valid against schema" in res.stdout

def test_cli_run_dry_run():
    mission_file = os.path.join(workspace, "examples", "mission.release.yaml")
    res = run_cli("run", "--dry-run", mission_file)
    assert res.returncode == 0
    assert "DRY RUN: Mission" in res.stdout

def test_cli_run_execution():
    mission_file = os.path.join(workspace, "examples", "mission.release.yaml")
    manifest_file = os.path.join(workspace, "examples", "INTELLIGENCE.yaml")
    res = run_cli("run", "--manifest", manifest_file, mission_file)
    assert res.returncode == 0
    assert "Invariant 1 enforced" in res.stdout

def test_cli_package():
    examples_dir = os.path.join(workspace, "examples")
    out_pkg = os.path.join(workspace, "data", "test-package.json")
    res = run_cli("package", examples_dir, "--output", out_pkg)
    assert res.returncode == 0
    assert "PACKAGED" in res.stdout
    assert os.path.exists(out_pkg)
    if os.path.exists(out_pkg):
        os.remove(out_pkg)

def test_cli_status():
    res = run_cli("status", "mission-release-prod")
    assert res.returncode == 0
    assert "MISSION STATUS" in res.stdout

def test_cli_status_real_file():
    mission_file = os.path.join(workspace, "examples", "mission.release.yaml")
    res = run_cli("status", mission_file)
    assert res.returncode == 0
    assert "MISSION CONTROL" in res.stdout
    assert "release-production" in res.stdout

def test_cli_audit():
    res = run_cli("audit")
    assert res.returncode == 0
    assert "AUDIT VERDICT: HEALTHY & VERIFIED" in res.stdout
    assert "14/14 Conformance Cases Passed" in res.stdout
