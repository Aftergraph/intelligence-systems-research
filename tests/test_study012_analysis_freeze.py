import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "data" / "study012_analysis_freeze.json"
SIDECAR = ROOT / "data" / "study012_analysis_freeze.json.sha256"


def test_analysis_freeze_artifact_is_integrity_bound():
    raw = FREEZE.read_bytes()
    assert SIDECAR.read_text().strip() == hashlib.sha256(raw).hexdigest()
    payload = json.loads(raw)
    assert payload["study_id"] == "STUDY-012"
    assert payload["experiment_id"] == "ICT-EXP-001"
    assert payload["gate"] == "G12-7"
    assert payload["freeze_version"] == "v1.0.0"
    assert payload["primary_comparison"] == ["I6", "I5"]
    assert payload["confirmatory_execution_authorized"] is False
    assert payload["empirical_conclusions"] == []


def test_frozen_analysis_and_golden_test_hashes_match_files():
    payload = json.loads(FREEZE.read_text())
    for key in ("analysis_script", "golden_test"):
        item = payload[key]
        path = ROOT / item["path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
