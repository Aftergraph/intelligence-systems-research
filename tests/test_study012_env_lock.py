"""G12-4: confirmatory-environment dependency-lock tests for ICT-EXP-001 (Issue #52).

Asserts the frozen lock file (data/study012_confirmatory_env_lock.json) is
intact AND that the current runtime matches it. A version drift fails loudly
instead of silently invalidating future confirmatory runs.
No execution of confirmatory workloads, no empirical conclusions.
"""
import hashlib
import json
import os
import platform
from importlib.metadata import version
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))

LOCK = Path(workspace) / "data" / "study012_confirmatory_env_lock.json"
LOCK_SHA = Path(workspace) / "data" / "study012_confirmatory_env_lock.json.sha256"


@pytest.fixture
def lock():
    with open(LOCK) as f:
        return json.load(f)


def test_lock_sha256_matches():
    h = hashlib.sha256()
    with open(LOCK, "rb") as f:
        h.update(f.read())
    assert h.hexdigest() == LOCK_SHA.read_text().strip()


def test_lock_gate_identity(lock):
    assert lock["gate"].startswith("G12-4")
    assert lock["experiment_id"] == "ICT-EXP-001"
    assert lock["freeze_version"] == "DRAFT"


def test_lock_policy_requires_refreeze_on_drift(lock):
    policy = lock["lock_policy"]
    assert "version bump" in policy and "sha256" in policy


def test_runtime_python_matches_lock(lock):
    current = f"{platform.python_version_tuple()[0]}.{platform.python_version_tuple()[1]}.{platform.python_version_tuple()[2]}"
    assert platform.python_version() == lock["environment"]["python"], (
        f"python drift: runtime {platform.python_version()} != lock {lock['environment']['python']}"
    )


def test_runtime_pytest_matches_lock(lock):
    assert version("pytest") == lock["environment"]["pytest"]


def test_runtime_openai_agents_matches_lock(lock):
    assert version("openai-agents") == lock["environment"]["openai_agents"]


def test_no_empirical_conclusions(lock):
    assert "No execution" in lock["_freeze_notice"]
    assert "no empirical conclusions" in lock["_freeze_notice"]
