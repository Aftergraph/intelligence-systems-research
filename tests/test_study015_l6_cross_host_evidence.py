import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
L5 = ROOT / "data" / "study015" / "l5_durable_recovery.json"
L6 = ROOT / "data" / "study015" / "l6_cross_host_failover.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_study015_l6_receipt_hash_is_reproducible():
    doc = _load(L6)
    receipt = dict(doc["receipt"])
    claimed = receipt.pop("causal_slice_sha256")
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    observed = hashlib.sha256(canonical.encode()).hexdigest()
    assert observed == claimed
    assert claimed == "0a1cc344c21becf0276cf41598943b6abd72ffd58bfb95f9e6c7369e1af3a8ff"


def test_study015_l6_predecessor_is_verified_l5():
    l5 = _load(L5)["receipt"]
    l6 = _load(L6)
    assert l6["predecessor"]["receipt_sha256"] == l5["causal_slice_sha256"]
    assert l6["receipt"]["prior_l5_receipt_sha256"] == l5["causal_slice_sha256"]
    assert l6["receipt"]["hostile"]["prior_l5_execution_context_rejected"] is True


def test_study015_l6_is_physically_cross_host():
    receipt = _load(L6)["receipt"]
    a = receipt["host_a"]
    b = receipt["host_b"]
    assert a["hostname"] == "vmi3517816"
    assert b["hostname"] == "vps-70333b3c"
    assert a["hostname"] != b["hostname"]
    assert a["machine_id_sha256"] != b["machine_id_sha256"]
    assert receipt["cross_host"]["hostname_changed"] is True
    assert receipt["cross_host"]["machine_identity_changed"] is True


def test_study015_l6_handoff_is_hash_bound_and_secret_free():
    doc = _load(L6)
    p = doc["provenance"]
    receipt = doc["receipt"]
    assert p["phase_a_manifest_sha256"] == receipt["handoff"]["phase_a_sha256"]
    assert p["phase_a_handoff_tar_sha256"] == "27704eee7a694fbafb4bbbd4f4e150907b4c953c087c55e45946ed6950c21db1"
    assert p["phase_a_artifact_zip_sha256"] == "56b4ede8036424e063e5259ad9663175a3ae404cb5939752939a859c3151f2fc"
    assert receipt["handoff"]["files_verified"] is True
    assert receipt["handoff"]["secrets_transferred"] is False
    assert receipt["handoff"]["fresh_host_b_secrets"] is True
    assert receipt["handoff"]["works_relocated"] is True
    assert receipt["handoff"]["tg_audit_chain_transferred"] is True


def test_study015_l6_same_causal_identity_survived_relocation():
    cross = _load(L6)["receipt"]["cross_host"]
    assert cross == {
        "durable_verified_outcome": True,
        "hostname_changed": True,
        "machine_identity_changed": True,
        "same_execution_context": True,
        "same_trace": True,
        "same_work": True,
        "same_works_execution": True,
        "single_external_effect": True,
    }


def test_study015_l6_exact_subject_matches_remote_readback():
    receipt = _load(L6)["receipt"]
    remote = receipt["proof_target"]["remote_readback"]
    assert receipt["proof_target"]["pull_request"] == 211
    assert remote == "0c280233565ba5c98d259679ba5ef6a2663b8283"
    assert receipt["identity"]["exact_subject"] == f"git:Aftergraph/runtime@{remote}"


def test_study015_l6_hostile_checks_all_passed():
    hostile = _load(L6)["receipt"]["hostile"]
    assert hostile == {
        "prior_l5_execution_context_rejected": True,
        "revoked_authority_rejected_before_egress": True,
        "stale_verification_head_rejected": True,
        "wrong_pdr_rejected": True,
    }


def test_study015_l6_claim_boundary_remains_fail_closed():
    doc = _load(L6)
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


def test_study015_l6_scheduling_history_is_not_hidden():
    p = _load(L6)["provenance"]
    assert p["superseded_phase_b_job_id"] == 108224114332
    assert p["superseded_phase_b_conclusion"] == "cancelled"
    assert "canonical Host B resume" in p["scheduling_note"]


def test_study015_l7_candidate_does_not_authorize_performance():
    gate = _load(L6)["next_gate_candidate"]
    assert gate["name"] == "L7_INDETERMINATE_EFFECT_RECONCILIATION"
    assert gate["performance_study"] is False
    assert gate["authorizes_g15_9"] is False
