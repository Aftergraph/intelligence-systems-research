import hashlib
import json
import math
from pathlib import Path

from experiments.system_one_acceleration.calibration import wilson_upper

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / "data" / "jar_exp_0015_active_protocol.json"
PROTOCOL = ROOT / "data" / "jar_exp_0015_protocol_v04.json"
DATASET = ROOT / "data" / "jar_exp_0015_dataset_v03.json"
MANIFEST = ROOT / "data" / "jar_exp_0015_split_manifest_v03.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def test_active_registry_points_only_to_protocol_v04():
    active = _load(ACTIVE)
    assert active["status"] == "ACTIVE_PREEXECUTION"
    assert active["active_protocol_ref"] == "data/jar_exp_0015_protocol_v04.json"
    assert active["active_protocol_git_blob_sha"] == _git_blob_sha(PROTOCOL)
    assert active["network_calls_authorized"] is False
    assert {x["protocol_ref"] for x in active["superseded"]} == {
        "data/jar_exp_0015_protocol_v01.json",
        "data/jar_exp_0015_protocol_v02.json",
        "data/jar_exp_0015_protocol_v03.json",
    }


def test_active_dataset_and_manifest_hashes_match_registry():
    active = _load(ACTIVE)
    assert hashlib.sha256(DATASET.read_bytes()).hexdigest() == active["active_dataset_sha256"]
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == active["active_split_manifest_sha256"]


def test_protocol_v04_preserves_v03_feasibility_with_v03_activation():
    p = _load(PROTOCOL)
    f = p["sample_size_feasibility"]
    assert p["schema_version"] == "jar-exp-0015.protocol/0.4"
    assert p["amendments"] == ["001", "002", "003"]
    assert f["v01_calibration_n"] == 24
    assert f["v01_holdout_n"] == 16
    assert f["v01_feasible"] is False
    assert f["v02_split_n_per_decision_type"] == 244
    assert math.ceil(244 * 0.30) == 74
    assert f["floor_accepted_n_at_30_percent"] == 74


def test_wilson_falsification_and_v03_feasibility_are_numerically_true():
    assert wilson_upper(0, 24) > 0.05
    assert wilson_upper(0, 16) > 0.05
    assert wilson_upper(0, 72) > 0.05
    assert wilson_upper(0, 73) <= 0.05
    assert wilson_upper(0, 74) <= 0.05


def test_protocol_v03_dataset_math_is_exact():
    p = _load(PROTOCOL)
    d = p["dataset"]
    assert d["cases_per_decision_type"] == 488
    assert d["calibration_per_decision_type"] == 244
    assert d["holdout_per_decision_type"] == 244
    assert d["total_calibration"] == 1952
    assert d["total_holdout"] == 1952
    assert d["total_cases"] == 3904
    assert len(d["decision_types"]) == 8


def test_v04_preserves_zero_network_authority():
    p = _load(PROTOCOL)
    active = _load(ACTIVE)
    assert p["network_calls_authorized"] is False
    assert active["network_calls_authorized"] is False
    assert p["authority_boundary"] == {
        "system_one_role": "ADVISORY_ONLY",
        "grants_authority": False,
        "grants_verification": False,
        "grants_execution_truth": False,
    }
