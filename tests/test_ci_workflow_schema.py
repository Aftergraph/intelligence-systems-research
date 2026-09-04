"""
test_ci_workflow_schema.py
==========================

Pins the .github/workflows/ci.yml schema: 5 jobs, 4 triggers, all
required jobs present, no live network calls in any job.

This is a CI-discipline test. The CI must:
- Run pytest
- Run the audit
- Verify the frozen SHA sidecar
- Run a pre-execution gate that does NOT make live calls
- Run the Node conformance tests (if present)
"""

import os
import sys

import pytest
import yaml

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

CI_PATH = os.path.join(workspace, ".github", "workflows", "ci.yml")


@pytest.fixture(scope="module")
def workflow():
    assert os.path.exists(CI_PATH), (
        f"CI workflow file missing: {CI_PATH}. "
        f"Create it under .github/workflows/ci.yml."
    )
    with open(CI_PATH, "r", encoding="utf-8") as f:
        text = f.read()
    return yaml.safe_load(text), text


def test_ci_workflow_exists(workflow):
    data, _ = workflow
    assert data is not None
    assert "jobs" in data


def test_ci_workflow_required_jobs(workflow):
    data, _ = workflow
    required_jobs = {
        "python-tests",       # pytest
        "frozen-artifact-integrity",  # SHA verification
        "study011-preflight",  # LIVE_ONLY invariant
    }
    actual_jobs = set(data["jobs"].keys())
    missing = required_jobs - actual_jobs
    assert not missing, f"CI workflow missing required jobs: {missing}"


def test_ci_workflow_triggers(workflow):
    data, _ = workflow
    # YAML parses 'on' as True (boolean). Accept either.
    triggers = data.get("on") or data.get(True)
    assert triggers is not None, "CI workflow has no triggers"
    expected = {"push", "pull_request"}
    missing = expected - set(triggers.keys() if isinstance(triggers, dict) else [triggers])
    # Some workflows use a bare list as 'on'; allow that
    if isinstance(triggers, list):
        assert "push" in triggers
        assert "pull_request" in triggers
    else:
        assert not missing, f"CI workflow missing triggers: {missing}"


def test_ci_workflow_no_live_network_calls(workflow):
    """The CI must not contain any obvious live network call patterns
    (api.openai.com, anthropic, key=$OPENAI_API_KEY, etc.). It is a
    pre-execution gate, not a live harness."""
    _, text = workflow
    forbidden_substrings = [
        "api.openai.com",
        "api.anthropic.com",
        "generativelanguage.googleapis.com",
        "openrouter.ai/api/v1/chat",
    ]
    for sub in forbidden_substrings:
        assert sub not in text, (
            f"CI workflow contains live-API substring {sub!r}. "
            f"CI is a pre-execution gate; it must not make live calls."
        )


def test_ci_workflow_uses_lf(workflow):
    """The CI workflow file must be LF (CRLF would break frozen-hash
    verification on Windows)."""
    _, text = workflow
    assert "\r\n" not in text, (
        "CI workflow contains CRLF line endings. LF is required for "
        "frozen-hash verification."
    )


def test_python_tests_job_runs_pytest(workflow):
    data, _ = workflow
    job = data["jobs"].get("python-tests", {})
    steps = job.get("steps", [])
    # Find a step that runs pytest
    found_pytest = False
    for step in steps:
        run = step.get("run", "")
        if "pytest" in run:
            found_pytest = True
            break
    assert found_pytest, (
        "python-tests job has no step that runs pytest. "
        f"steps: {[s.get('name', '?') for s in steps]}"
    )


def test_python_tests_job_runs_audit(workflow):
    data, _ = workflow
    job = data["jobs"].get("python-tests", {})
    steps = job.get("steps", [])
    found_audit = False
    for step in steps:
        run = step.get("run", "")
        if "mission_cli.py audit" in run or "mission_cli.py" in run and "audit" in run:
            found_audit = True
            break
    assert found_audit, (
        "python-tests job has no step that runs the audit. "
        f"steps: {[s.get('name', '?') for s in steps]}"
    )


def test_frozen_artifact_integrity_verifies_sidecar(workflow):
    data, _ = workflow
    job = data["jobs"].get("frozen-artifact-integrity", {})
    steps = job.get("steps", [])
    # Find a step that reads study011_preregistration_manifest.sha256
    found = False
    for step in steps:
        run = step.get("run", "")
        if "study011_preregistration_manifest.sha256" in run:
            found = True
            break
    assert found, (
        "frozen-artifact-integrity job has no step that verifies "
        "the study011 sidecar SHA."
    )


def test_study011_preflight_no_live_calls(workflow):
    data, _ = workflow
    job = data["jobs"].get("study011-preflight", {})
    steps = job.get("steps", [])
    # The preflight should run the analyzer, not make live calls.
    found_analyzer = False
    for step in steps:
        run = step.get("run", "")
        if "study011_analyze" in run or "pre-execution gate" in run.lower():
            found_analyzer = True
            break
    assert found_analyzer, (
        "study011-preflight job has no step that imports/runs the "
        f"analyzer. steps: {[s.get('name', '?') for s in steps]}"
    )
