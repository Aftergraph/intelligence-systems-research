import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
L3 = ROOT / "data" / "study015" / "live_causal_slice_l3.json"
L4 = ROOT / "data" / "study015" / "l4_repeatability.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_study015_l4_receipt_hash_is_reproducible():
    doc = _load(L4)
    receipt = dict(doc["receipt"])
    claimed = receipt.pop("causal_slice_sha256")
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    observed = hashlib.sha256(canonical.encode()).hexdigest()
    assert observed == claimed
    assert claimed == "31d734b5a958f13a4a9db8306f8fefa4e147dc26a066d78df4fea1ed0fd28e96"


def test_study015_l4_predecessor_is_exact_l3_receipt():
    l3 = _load(L3)["receipt"]
    l4 = _load(L4)
    repeatability = l4["receipt"]["repeatability"]
    assert repeatability["prior_l3_causal_slice_sha256"] == l3["causal_slice_sha256"]
    assert repeatability["prior_l3_execution_context_id"] == l3["identity"]["execution_context_id"]
    assert l4["predecessor"]["receipt_sha256"] == l3["causal_slice_sha256"]


def test_study015_l4_identity_is_fresh_relative_to_l3():
    l3 = _load(L3)["receipt"]["identity"]
    l4 = _load(L4)["receipt"]["identity"]
    for key in ("execution_context_id", "mission_id", "action_id", "effect_id", "causal_id", "exact_subject"):
        assert l4[key] != l3[key], key


def test_study015_l4_exact_subject_matches_remote_readback():
    receipt = _load(L4)["receipt"]
    remote = receipt["proof_target"]["remote_readback"]
    assert remote == receipt["proof_target"]["sha_b"]
    assert receipt["identity"]["exact_subject"] == f"git:Aftergraph/runtime@{remote}"


def test_study015_l4_all_fresh_flags_are_strict_true():
    repeatability = _load(L4)["receipt"]["repeatability"]
    fresh = {k: v for k, v in repeatability.items() if k.startswith("fresh_")}
    assert fresh
    assert all(type(v) is bool and v is True for v in fresh.values())


def test_study015_l4_hostile_checks_and_seams_all_passed():
    receipt = _load(L4)["receipt"]
    assert receipt["hostile"]["prior_l3_execution_context_rejected"] is True
    assert all(receipt["hostile"].values())
    assert all(receipt["seams"].values())


def test_study015_l4_claim_boundary_remains_fail_closed():
    doc = _load(L4)
    receipt = doc["receipt"]
    assert receipt["performance_claim"] is False
    assert receipt["g15_9_authorized"] is False
    assert receipt["production_deployment"] is False
    assert doc["claim_boundary"] == {
        "performance_claim": False,
        "g15_9_authorized": False,
        "production_deployment": False,
        "world_first_claim": False,
        "industry_superiority_claim": False,
    }


def test_study015_l5_candidate_does_not_authorize_performance():
    gate = _load(L4)["next_gate_candidate"]
    assert gate["name"] == "L5_DURABLE_CAUSAL_RECOVERY"
    assert gate["performance_study"] is False
    assert gate["authorizes_g15_9"] is False
