import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "study015" / "live_causal_slice_l3.json"


def _load():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_study015_l3_receipt_hash_is_reproducible():
    doc = _load()
    receipt = dict(doc["receipt"])
    claimed = receipt.pop("causal_slice_sha256")
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    observed = hashlib.sha256(canonical.encode()).hexdigest()
    assert observed == claimed
    assert claimed == "39a4e862030476ad4585fd70038056c8ad3e2b719e645ca64b86a477cdfb230d"


def test_study015_l3_exact_subject_matches_remote_readback():
    doc = _load()
    receipt = doc["receipt"]
    remote = receipt["proof_target"]["remote_readback"]
    assert remote == receipt["proof_target"]["sha_b"]
    assert receipt["identity"]["exact_subject"] == f"git:Aftergraph/runtime@{remote}"


def test_study015_l3_all_declared_seams_and_hostile_checks_passed():
    doc = _load()
    receipt = doc["receipt"]
    assert all(receipt["seams"].values())
    assert all(receipt["hostile"].values())


def test_study015_l3_claim_boundary_remains_fail_closed():
    doc = _load()
    receipt = doc["receipt"]
    boundary = doc["claim_boundary"]
    assert receipt["performance_claim"] is False
    assert receipt["g15_9_authorized"] is False
    assert receipt["production_deployment"] is False
    assert boundary == {
        "performance_claim": False,
        "g15_9_authorized": False,
        "production_deployment": False,
        "world_first_claim": False,
        "industry_superiority_claim": False,
    }


def test_study015_l4_candidate_cannot_authorize_performance():
    doc = _load()
    gate = doc["next_gate_candidate"]
    assert gate["name"] == "L4_INDEPENDENT_REPEATABILITY"
    assert gate["performance_study"] is False
    assert gate["authorizes_g15_9"] is False
