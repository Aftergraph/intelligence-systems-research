"""
test_dry_run_harness_script.py
==============================

Pins experiments/live_benchmark/dry_run_test.py as proper pytest
tests. The script validates the STUDY-008 live-benchmark harness
in dry-run mode: all 7 conditions (A-G) must generate a manifest
with a SHA-256 and the correct condition code.

Contract pinned:
- Each of the 7 conditions generates a manifest on disk.
- Every manifest has a non-null manifest_sha256.
- Every manifest records its condition code.
- Dry-run manifests are the STUDY-008 evidence class; the analyzer
  must classify them INVALID_PROTOCOL / EXCLUDED, never LIVE_VALID
  (LIVE_ONLY invariant — see tests/test_study011_analyze.py).
"""

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

lb_path = os.path.join(workspace, "experiments", "live_benchmark")
if lb_path not in sys.path:
    sys.path.insert(0, lb_path)

spec = importlib.util.spec_from_file_location(
    "dry_run_test_module",
    os.path.join(lb_path, "dry_run_test.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


EXPECTED_CONDITIONS = ["A", "B", "C", "D", "E", "F", "G"]


@pytest.fixture(scope="module")
def dry_run_output():
    """Run the dry-run harness for all 7 conditions; return the list of
    (manifest_path, condition, sha) tuples."""
    output_dir = os.path.join(workspace, "data", "live_benchmark_dry_runs")
    results = []
    for cond_code in EXPECTED_CONDITIONS:
        manifest_path, verified = mod.run_condition_trial(
            condition=cond_code,
            task=mod.build_sample_task(),
            model_client=None,  # not used in dry-run
            output_dir=output_dir,
            dry_run=True,
        ) if hasattr(mod, "build_sample_task") else (None, None)
        results.append((cond_code, manifest_path))
    return results


def test_dry_run_script_is_importable():
    """The script must import without network access."""
    assert mod is not None


def test_all_seven_conditions_generate_manifests(tmp_path):
    """Each condition A-G must produce a manifest file with SHA + condition."""
    from experiments.live_benchmark.harness import (
        LiveModelClient, run_condition_trial, CONDITIONS,
    )
    output_dir = str(tmp_path)
    client = LiveModelClient(provider="openai", model_id="gpt-4o")
    sample_task = {
        "id": "TASK-PYTEST-01",
        "prompt": "Fix null pointer in auth middleware.",
        "mission": {
            "apiVersion": "intelligence.systems/v0alpha1",
            "kind": "Mission",
            "metadata": {"id": "mission-pytest-01", "version": 1},
            "objective": {"outcome": "Fix null pointer bug."},
            "success": {"all": ["tests_passed"]},
            "budget": {"tokens": {"max": 10000}},
        },
        "delegation": {
            "id": "del-pytest-01",
            "principal": "urn:principal:lead-dev",
            "delegate": "urn:agent:coder-bot",
            "purpose": "mission-pytest-01",
            "scope": {"allowed_capabilities": ["mcp://git/*", "mcp://pytest/*"]},
            "valid_from": "2026-09-01T00:00:00Z",
            "expires_at": "2026-09-30T00:00:00Z",
        },
    }
    for cond_code in EXPECTED_CONDITIONS:
        manifest_path, verified = run_condition_trial(
            condition=cond_code,
            task=sample_task,
            model_client=client,
            output_dir=output_dir,
            dry_run=True,
        )
        assert os.path.exists(manifest_path), (
            f"Condition {cond_code} produced no manifest at {manifest_path}"
        )
        data = json.load(open(manifest_path, encoding="utf-8"))
        assert data["manifest_sha256"] is not None
        assert data["condition"] == cond_code


def test_dry_run_directory_still_present_in_repo():
    """The 299 frozen STUDY-008 dry-run JSONs must not be deleted."""
    d = Path(workspace) / "data" / "live_benchmark_dry_runs"
    assert d.exists()
    n = len(list(d.glob("*.json")))
    assert n >= 299, (
        f"Only {n} dry-run JSONs remain (expected >= 299). "
        f"These are STUDY-008 evidence; do not delete."
    )
