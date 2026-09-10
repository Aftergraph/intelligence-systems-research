"""G12-7: pilot dry-run report tests for ICT-EXP-001 (Issue #52).

Asserts the dry-run report is intact, covers all fixtures, plans (never
executes) all 6 comparison pairs, references the frozen manifest, and contains
zero empirical conclusions. No execution, no live APIs.
"""
import hashlib
import json
import os
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))

REPORT = Path(workspace) / "data" / "study012_pilot_dryrun_report.json"
REPORT_SHA = Path(workspace) / "data" / "study012_pilot_dryrun_report.json.sha256"
MANIFEST = Path(workspace) / "data" / "study012_workload_manifest.json"


@pytest.fixture
def report():
    with open(REPORT) as f:
        return json.load(f)


def test_report_sha256_matches():
    h = hashlib.sha256()
    with open(REPORT, "rb") as f:
        h.update(f.read())
    assert h.hexdigest() == REPORT_SHA.read_text().strip()


def test_report_gate_identity(report):
    assert report["gate"].startswith("G12-7")
    assert report["experiment_id"] == "ICT-EXP-001"
    assert report["freeze_version"] == "DRAFT"


def test_report_references_frozen_manifest(report):
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["freeze_version"] == "v1.0.0"
    assert report["manifest_root_hash"] == manifest["root_hash"]
    assert report["fixtures_validated"] == manifest["total_count"] == 12


def test_report_covers_six_pairs(report):
    pairs = report["comparison_pairs"]
    assert len(pairs) == 6
    covered = sorted(w for p in pairs for w in p["pair"])
    manifest = json.loads(MANIFEST.read_text())
    assert covered == sorted(w["workload_id"] for w in manifest["workloads"])


def test_report_no_live_apis(report):
    for p in report["comparison_pairs"]:
        assert p["live_api_calls"] == 0
        assert p["status"] == "PLANNED-NOT-EXECUTED"
    raw = REPORT.read_text()
    assert "http://" not in raw and "https://" not in raw


def test_report_no_execution_no_conclusions(report):
    assert report["execution_occurred"] is False
    assert report["empirical_conclusions"] == []
    assert "DRY-RUN ONLY" in report["_notice"]
