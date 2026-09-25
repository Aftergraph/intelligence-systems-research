import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
L4 = ROOT / "data" / "study015" / "l4_repeatability.json"
L5 = ROOT / "data" / "study015" / "l5_durable_recovery.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_study015_l5_receipt_hash_is_reproducible():
    doc = _load(L5)
    receipt = dict(doc["receipt"])
    claimed = receipt.pop("causal_slice_sha256")
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    observed = hashlib.sha256(canonical.encode()).hexdigest()
    assert observed == claimed
    assert claimed == "9bb6d0ed6833d09f7b5e9e0d2b70b3eeb7c3aba922fd887eed3c1e91fced7178"


def test_study015_l5_predecessor_is_final_l4():
    l4 = _load(L4)["receipt"]
    l5 = _load(L5)
    assert l5["predecessor"]["receipt_sha256"] == l4["causal_slice_sha256"]
    assert l5["receipt"]["durability"]["prior_l4_causal_slice_sha256"] == l4["causal_slice_sha256"]
    assert l5["receipt"]["durability"]["prior_l4_execution_context_id"] == l4["identity"]["execution_context_id"]


def test_study015_l5_exact_subject_matches_remote_readback():
    receipt = _load(L5)["receipt"]
    remote = receipt["proof_target"]["remote_readback"]
    assert receipt["proof_target"]["pull_request"] == 209
    assert remote == "efc536b1095715124e2a5455161792f030c974a6"
    assert receipt["identity"]["exact_subject"] == f"git:Aftergraph/runtime@{remote}"


def test_study015_l5_every_boolean_durability_invariant_is_true():
    durability = _load(L5)["receipt"]["durability"]
    bools = {k: v for k, v in durability.items() if not k.startswith("prior_l4_")}
    assert len(bools) >= 20
    assert all(type(v) is bool and v is True for v in bools.values())


def test_study015_l5_single_effect_and_idempotent_acceptance_are_pinned():
    durability = _load(L5)["receipt"]["durability"]
    assert durability["single_persisted_git_egress_completion"] is True
    assert durability["post_restart_authority_revalidated_without_effect"] is True
    assert durability["mission_acceptance_retry_idempotent"] is True
    assert durability["same_tg_audit_file_after_restart"] is True
    assert durability["tg_audit_chain_verified_after_restart"] is True


def test_study015_l5_hostile_checks_and_seams_all_passed():
    receipt = _load(L5)["receipt"]
    assert all(receipt["hostile"].values())
    assert all(receipt["seams"].values())


def test_study015_l5_claim_boundary_remains_fail_closed():
    doc = _load(L5)
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


def test_study015_l5_falsification_history_is_not_hidden():
    p = _load(L5)["provenance"]
    assert p["superseded_falsification_run_id"] == 36168414366
    assert "memory-only" in p["superseded_falsification_reason"]


def test_study015_l6_candidate_does_not_authorize_performance():
    gate = _load(L5)["next_gate_candidate"]
    assert gate["name"] == "L6_INDETERMINATE_EFFECT_RECONCILIATION"
    assert gate["performance_study"] is False
    assert gate["authorizes_g15_9"] is False
