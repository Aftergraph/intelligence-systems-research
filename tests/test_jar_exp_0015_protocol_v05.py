import hashlib
import json
import math
from pathlib import Path

from experiments.system_one_acceleration.calibration import wilson_upper

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / "data" / "jar_exp_0015_active_protocol.json"
PROTOCOL = ROOT / "data" / "jar_exp_0015_protocol_v05.json"
DATASET = ROOT / "data" / "jar_exp_0015_dataset_v03.json"
MANIFEST = ROOT / "data" / "jar_exp_0015_split_manifest_v03.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def test_active_registry_points_only_to_protocol_v05():
    active = _load(ACTIVE)
    assert active["status"] == "ACTIVE_PREEXECUTION"
    assert active["active_protocol_ref"] == "data/jar_exp_0015_protocol_v05.json"
    assert active["active_protocol_git_blob_sha"] == _git_blob_sha(PROTOCOL)
    assert active["network_calls_authorized"] is False
    assert {x["protocol_ref"] for x in active["superseded"]} == {
        "data/jar_exp_0015_protocol_v01.json",
        "data/jar_exp_0015_protocol_v02.json",
        "data/jar_exp_0015_protocol_v03.json",
        "data/jar_exp_0015_protocol_v04.json",
    }


def test_active_dataset_and_manifest_hashes_match_registry():
    active = _load(ACTIVE)
    assert hashlib.sha256(DATASET.read_bytes()).hexdigest() == active["active_dataset_sha256"]
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == active["active_split_manifest_sha256"]


def test_protocol_v05_preserves_sample_size_correction():
    p = _load(PROTOCOL)
    f = p["sample_size_feasibility"]
    assert p["schema_version"] == "jar-exp-0015.protocol/0.5"
    assert p["amendments"] == ["001", "002", "003", "004"]
    assert f["v01_feasible"] is False
    assert f["v02_split_n_per_decision_type"] == 244
    assert math.ceil(244 * 0.30) == 74
    assert f["floor_accepted_n_at_30_percent"] == 74
    assert wilson_upper(0, 72) > 0.05
    assert wilson_upper(0, 73) <= 0.05
    assert wilson_upper(0, 74) <= 0.05


def test_protocol_v05_binds_projection_visible_dataset():
    p = _load(PROTOCOL)
    d = p["dataset"]
    assert d["dataset_ref"] == "data/jar_exp_0015_dataset_v03.json"
    assert d["dataset_sha256"] == "51846d8b4a95540a8e182a823a7256fbdd69d61b3244f89e078db77ad7e0496e"
    assert d["split_manifest_ref"] == "data/jar_exp_0015_split_manifest_v03.json"
    assert d["split_manifest_sha256"] == "46b0123ed31b27d80823e518bef9e24bf4f1cc672f763d7b75e446698a00b745"
    assert d["total_cases"] == 3904
    assert d["total_calibration"] == 1952
    assert d["total_holdout"] == 1952


def test_protocol_v05_projection_contract_does_not_widen_authority():
    p = _load(PROTOCOL)
    projection = p["provider_projection"]
    assert projection["allowed_dataset_provider_fields"] == ["scenario"]
    assert projection["dataset_semantics_must_survive_projection"] is True
    assert projection["authority_change"] is False
    assert set(projection["verbatim_expected_label_forbidden_for"]) == {
        "route_model", "route_tool_family"
    }
    assert p["authority_boundary"] == {
        "system_one_role": "ADVISORY_ONLY",
        "grants_authority": False,
        "grants_verification": False,
        "grants_execution_truth": False,
    }


def test_v04_preserves_zero_network_authority():
    assert _load(PROTOCOL)["network_calls_authorized"] is False
    assert _load(ACTIVE)["network_calls_authorized"] is False


def test_protocol_v05_separates_contract_execution_stages():
    p = _load(PROTOCOL)
    stages = p["execution_stages"]
    assert stages["abc_calibration"]["provider_calls"] == 1952
    assert stages["abc_calibration"]["contract_mode"] == "original_contracts"
    assert stages["abc_calibration"]["authorized_by_current_owner_approval"] is True
    assert stages["arm_d_revised_contract_calibration"]["provider_calls"] == 732
    assert stages["arm_d_revised_contract_calibration"]["max_cost_usd"] == 2.02
    assert stages["arm_d_revised_contract_calibration"]["authorized_by_current_owner_approval"] is False
    assert stages["holdout"]["authorized"] is False
