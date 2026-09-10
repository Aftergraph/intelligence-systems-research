"""
test_study012_preconfirmatory_freeze.py
=========================================

Pre-run gate: pins the STUDY-012 ICT-EXP-001 DRAFT freeze snapshot — workload
manifest SHA-256 and manifest integrity — and enforces the no-silent-change
invariant via data/study012_workload_manifest.json + .sha256.

The manifest is written at gate time; any subsequent change to the frozen
manifest changes the hash and the study must be re-gated.

This is a DRAFT pre-registration gate only. No execution has occurred. No
empirical conclusions are asserted or implied.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

MANIFEST = Path(workspace) / "data" / "study012_workload_manifest.json"
SHA_FILE = Path(workspace) / "data" / "study012_workload_manifest.json.sha256"


def file_hash(p: Path) -> str:
    """SHA-256 of file bytes, lowercase hex."""
    return hashlib.sha256(p.read_bytes()).hexdigest()


def compute_manifest_sha() -> str:
    """SHA-256 of the canonical workload manifest file on disk."""
    if not MANIFEST.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST}")
    return file_hash(MANIFEST)


def read_stored_sha() -> str:
    """Read the single-line SHA-256 from the .sha256 sidecar file."""
    if not SHA_FILE.exists():
        raise FileNotFoundError(f"SHA sidecar not found: {SHA_FILE}")
    return SHA_FILE.read_text(encoding="utf-8").strip()


def load_manifest() -> dict:
    """Load and return the parsed workload manifest."""
    if not MANIFEST.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST}")
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)


FROZEN_FILES = [
    "data/study012_workload_manifest.json",
    "data/study012_workload_manifest.json.sha256",
    "STUDY-012-ICT-PREREGISTRATION.md",
]


@pytest.fixture(scope="module")
def manifest_sha():
    """The live SHA-256 of the manifest on disk."""
    return compute_manifest_sha()


@pytest.fixture(scope="module")
def stored_sha():
    """The SHA-256 recorded in the .sha256 sidecar file."""
    return read_stored_sha()


@pytest.fixture(scope="module")
def manifest():
    """The parsed workload manifest."""
    return load_manifest()


# ── Blocker A: manifest file integrity ──────────────────────────────────────


def test_manifest_file_exists(manifest_sha):
    """The workload manifest must exist and be hashably readable."""
    assert MANIFEST.exists(), f"Manifest missing: {MANIFEST}"


def test_sha256_sidecar_exists(stored_sha):
    """The .sha256 sidecar file must exist alongside the manifest."""
    assert SHA_FILE.exists(), f"SHA sidecar missing: {SHA_FILE}"


def test_sha256_sidecar_matches_manifest(manifest_sha, stored_sha):
    """
    Blocker #5 hard invariant: the stored SHA-256 in the .sha256 file must
    exactly match the live SHA-256 of the manifest on disk. Any silent edit
    to the manifest breaks this invariant and re-freezing is required.
    """
    assert manifest_sha == stored_sha, (
        f"SHA-256 MISMATCH: manifest on disk = {manifest_sha}, "
        f"stored in .sha256 = {stored_sha}. "
        "Re-freeze required: recompute SHA-256 and update .sha256."
    )


# ── Blocker B: manifest schema and content invariants ───────────────────────


def test_manifest_study_id(manifest):
    assert manifest.get("study_id") == "STUDY-012", (
        f"Expected study_id 'STUDY-012', got {manifest.get('study_id')}"
    )


def test_manifest_experiment_id(manifest):
    assert manifest.get("experiment_id") == "ICT-EXP-001", (
        f"Expected experiment_id 'ICT-EXP-001', got {manifest.get('experiment_id')}"
    )


def test_manifest_freeze_version_draft(manifest):
    assert manifest.get("freeze_version") == "DRAFT", (
        f"Expected freeze_version 'DRAFT', got {manifest.get('freeze_version')}"
    )


def test_manifest_workload_type_synthetic_only(manifest):
    assert manifest.get("workload_type") == "synthetic_only", (
        f"Expected workload_type 'synthetic_only', got {manifest.get('workload_type')}"
    )


def test_manifest_comparison_i6_vs_i5(manifest):
    comparison = manifest.get("comparison", "")
    assert "I6" in comparison and "I5" in comparison, (
        f"Expected I6-vs-I5 comparison, got: {comparison}"
    )


def test_manifest_total_count(manifest):
    assert manifest.get("total_count") == 12, (
        f"Expected 12 workloads (6 threat classes x 2 conditions), "
        f"got {manifest.get('total_count')}"
    )


def test_manifest_workloads_list(manifest):
    workloads = manifest.get("workloads", [])
    assert len(workloads) == 12, (
        f"Expected 12 workload entries, got {len(workloads)}"
    )


def test_manifest_workload_ids(manifest):
    """Workload IDs must follow S12-<THREAT>-<CONDITION> naming."""
    expected_ids = [
        "S12-IC1-I5", "S12-IC1-I6",
        "S12-IC2-I5", "S12-IC2-I6",
        "S12-IC3-I5", "S12-IC3-I6",
        "S12-IC4-I5", "S12-IC4-I6",
        "S12-IC5-I5", "S12-IC5-I6",
        "S12-IC6-I5", "S12-IC6-I6",
    ]
    actual_ids = sorted(w["workload_id"] for w in manifest["workloads"])
    assert actual_ids == sorted(expected_ids), (
        f"Workload ID mismatch. Expected {sorted(expected_ids)}, "
        f"got {actual_ids}"
    )


def test_manifest_has_sha256_placeholders(manifest):
    """
    DRAFT manifest entries use 'PLACEHOLDER' for SHA-256 hashes because no
    execution has occurred and fixture content is not yet defined. This test
    verifies the DRAFT structure rather than asserting real hashes.
    """
    for w in manifest["workloads"]:
        assert w.get("sha256") == "PLACEHOLDER", (
            f"Expected 'PLACEHOLDER' sha256 for {w['workload_id']} "
            f"in DRAFT manifest, got {w.get('sha256')}"
        )


def test_manifest_has_acceptance_criteria_placeholders(manifest):
    for w in manifest["workloads"]:
        assert w.get("acceptance_criteria_hash") == "PLACEHOLDER", (
            f"Expected 'PLACEHOLDER' acceptance_criteria_hash for "
            f"{w['workload_id']} in DRAFT manifest"
        )


def test_manifest_uses_synthetic_fixtures(manifest):
    """DRAFT workload fixture_hashes use 'PLACEHOLDER' values."""
    for w in manifest["workloads"]:
        fixture_hashes = w.get("fixture_hashes", {})
        for key, val in fixture_hashes.items():
            assert val == "PLACEHOLDER", (
                f"Expected 'PLACEHOLDER' for {w['workload_id']}."
                f"fixture_hashes.{key} in DRAFT manifest, got {val}"
            )


def test_manifest_threat_class_coverage(manifest):
    """All six PAPER 05 §6 threat classes must be represented."""
    families = {w["task_family"] for w in manifest["workloads"]}
    expected_families = {
        "Cross-Agent Collusion (IC-1)",
        "Unauthorized Externalization (IC-2)",
        "Topology Self-Expansion (IC-3)",
        "Trajectory Tampering (IC-4)",
        "Authority Laundering (IC-5)",
        "Revocation Failure (IC-6)",
    }
    assert families == expected_families, (
        f"Threat class coverage mismatch. Expected {expected_families}, "
        f"got {families}"
    )


def test_manifest_condition_pairing(manifest):
    """Each I5 workload must have a paired I6 workload with matching comparison_pair."""
    by_id = {w["workload_id"]: w for w in manifest["workloads"]}
    for w in manifest["workloads"]:
        condition = w["condition"]
        pair_id = w["comparison_pair"]
        assert pair_id in by_id, (
            f"{w['workload_id']}: comparison_pair {pair_id} not found in manifest"
        )
        pair = by_id[pair_id]
        assert pair["condition"] != condition, (
            f"{w['workload_id']}: comparison_pair {pair_id} has same condition "
            f"({condition}) — must be the opposite condition"
        )
        assert pair["comparison_pair"] == w["workload_id"], (
            f"{w['workload_id']}: comparison_pair {pair_id} does not point back "
            f"to {w['workload_id']}"
        )
        assert pair["task_family"] == w["task_family"], (
            f"{w['workload_id']}: comparison_pair {pair_id} has different "
            f"task_family ({pair['task_family']} vs {w['task_family']})"
        )


def test_manifest_synthetic_only_flag(manifest):
    """Every workload in a DRAFT synthetic-only manifest must be flagged synthetic_only."""
    for w in manifest["workloads"]:
        assert w.get("synthetic_only") is True, (
            f"{w['workload_id']}: expected synthetic_only=True in DRAFT manifest"
        )


def test_manifest_description_mentions_synthetic(manifest):
    """Every workload description must note 'synthetic workload: no live API calls'."""
    for w in manifest["workloads"]:
        desc = w.get("description", "").lower()
        assert "synthetic" in desc and "no live" in desc, (
            f"{w['workload_id']}: description must mention synthetic/no-live nature"
        )


def test_manifest_counts_by_family(manifest):
    """counts_by_family must reflect 2 workloads per threat class."""
    counts = manifest.get("counts_by_family", {})
    expected = {
        "Cross-Agent Collusion (IC-1)": 2,
        "Unauthorized Externalization (IC-2)": 2,
        "Topology Self-Expansion (IC-3)": 2,
        "Trajectory Tampering (IC-4)": 2,
        "Authority Laundering (IC-5)": 2,
        "Revocation Failure (IC-6)": 2,
    }
    assert counts == expected, (
        f"counts_by_family mismatch. Expected {expected}, got {counts}"
    )


def test_manifest_token_check_placeholder(manifest):
    """DRAFT token_check must have zero min/max with all_lte_2000 true."""
    tc = manifest.get("token_check", {})
    assert tc.get("max_tokens") == 0
    assert tc.get("min_tokens") == 0
    assert tc.get("all_lte_2000") is True
    assert tc.get("per_workload") == []


# ── Blocker C: pre-registration document invariants ─────────────────────────


def test_preregistration_exists():
    """STUDY-012-ICT-PREREGISTRATION.md must exist."""
    pr = Path(workspace) / "STUDY-012-ICT-PREREGISTRATION.md"
    assert pr.exists(), f"Pre-registration document missing: {pr}"


def test_preregistration_status_draft():
    """Pre-registration document must declare DRAFT status."""
    pr_text = (Path(workspace) / "STUDY-012-ICT-PREREGISTRATION.md").read_text(
        encoding="utf-8"
    )
    assert "DRAFT" in pr_text, (
        "Pre-registration document must declare DRAFT status"
    )


def test_preregistration_zero_empirical_claims():
    """Pre-registration must contain explicit zero-empirical-conclusions disclaimer."""
    pr_text = (Path(workspace) / "STUDY-012-ICT-PREREGISTRATION.md").read_text(
        encoding="utf-8"
    )
    assert "zero empirical conclusions" in pr_text.lower() or (
        "no empirical conclusions" in pr_text.lower()
    ), (
        "Pre-registration must explicitly disclaim any empirical conclusions"
    )


def test_preregistration_g12_1_present():
    """Pre-registration must mark G12-1 as PRESENT."""
    pr_text = (Path(workspace) / "STUDY-012-ICT-PREREGISTRATION.md").read_text(
        encoding="utf-8"
    )
    assert "G12-1" in pr_text and "PRESENT" in pr_text, (
        "Pre-registration must mark G12-1 as PRESENT"
    )


def test_preregistration_g12_2_through_10_pending():
    """Pre-registration must mark G12-2 through G12-10 as PENDING."""
    pr_text = (Path(workspace) / "STUDY-012-ICT-PREREGISTRATION.md").read_text(
        encoding="utf-8"
    )
    for i in range(2, 11):
        assert f"G12-{i}" in pr_text, (
            f"Pre-registration must mention G12-{i}"
        )
    assert "PENDING" in pr_text, (
        "Pre-registration must declare PENDING status for G12-2 through G12-10"
    )


def test_preregistration_narrow_or_reject_allowed():
    """Pre-registration must explicitly allow NARROW-or-REJECT outcomes."""
    pr_text = (Path(workspace) / "STUDY-012-ICT-PREREGISTRATION.md").read_text(
        encoding="utf-8"
    )
    assert "NARROW-or-REJECT" in pr_text or (
        "narrow or reject" in pr_text.lower()
    ), (
        "Pre-registration must allow NARROW-or-REJECT outcomes by design"
    )


def test_preregistration_not_study012_custom_agent():
    """
    This pre-registration must not conflate with STUDY-012-CUSTOM-AGENT-EFFICIENCY.
    The document must explicitly distinguish the two studies.
    """
    pr_text = (Path(workspace) / "STUDY-012-ICT-PREREGISTRATION.md").read_text(
        encoding="utf-8"
    )
    assert "CUSTOM-AGENT-EFFICIENCY" in pr_text or (
        "custom agent" in pr_text.lower() and "efficiency" in pr_text.lower()
    ), (
        "Pre-registration must explicitly distinguish from "
        "STUDY-012-CUSTOM-AGENT-EFFICIENCY"
    )


# ── Blocker D: no-silent-change invariant for frozen sidecar ─────────────────


def test_no_silent_change_manifest_sha(manifest_sha, stored_sha):
    """
    Re-check: even at test time, the sidecar SHA must match the manifest.
    This is the no-silent-change invariant carried by the .sha256 file.
    """
    assert manifest_sha == stored_sha, (
        "No-silent-change invariant violated: manifest SHA changed since freeze."
    )


# ── Blocker E: DRAFT-only sanity checks ──────────────────────────────────────


def test_manifest_has_freeze_notice(manifest):
    """Manifest must carry a freeze notice explaining the DRAFT status."""
    notice = manifest.get("_freeze_notice", "")
    assert "DRAFT" in notice
    assert "NO silent edits" in notice or "no silent" in notice.lower()


def test_manifest_has_canonical_json_method(manifest):
    """Manifest must document the canonical JSON method used for root hash."""
    assert "canonical_json_method" in manifest
    assert "sort_keys" in manifest["canonical_json_method"]
    assert "separators" in manifest["canonical_json_method"]


def test_manifest_has_root_hash_method(manifest):
    """Manifest must document the root hash computation method."""
    assert "root_hash_method" in manifest
    assert "sha256" in manifest["root_hash_method"]


def test_manifest_root_hash_is_placeholder(manifest):
    """DRAFT manifest root_hash is 'PLACEHOLDER' until freeze."""
    assert manifest.get("root_hash") == "PLACEHOLDER", (
        f"Expected root_hash 'PLACEHOLDER' in DRAFT, got {manifest.get('root_hash')}"
    )


def test_manifest_created_utc_is_set(manifest):
    """Manifest must have a created_utc timestamp."""
    assert manifest.get("created_utc"), (
        "Manifest must have a created_utc field"
    )


# ── G12-2: I0 opportunity-reachability matrix ──────────────────────────────────

MATRIX = Path(workspace) / "data" / "study012_i0_opportunity_matrix.json"
MATRIX_SHA = Path(workspace) / "data" / "study012_i0_opportunity_matrix.json.sha256"


@pytest.fixture
def matrix():
    with open(MATRIX) as f:
        return json.load(f)


def test_i0_matrix_sha256_matches(matrix):
    """No-silent-change invariant for the G12-2 matrix file."""
    h = hashlib.sha256()
    with open(MATRIX, "rb") as f:
        h.update(f.read())
    assert h.hexdigest() == MATRIX_SHA.read_text().strip()


def test_i0_matrix_gate_identity(matrix):
    assert matrix.get("gate", "").startswith("G12-2")
    assert matrix.get("experiment_id") == "ICT-EXP-001"
    assert matrix.get("freeze_version") == "DRAFT"


def test_i0_matrix_covers_all_manifest_scenarios(matrix, manifest):
    """Every scenario in the workload manifest must have an I0 entry."""
    manifest_scenarios = set(manifest.get("adversarial_scenarios", []))
    matrix_scenarios = {e["scenario"] for e in matrix["i0_reachability"]}
    assert manifest_scenarios <= matrix_scenarios, (
        f"Missing I0 entries: {manifest_scenarios - matrix_scenarios}"
    )


def test_i0_all_in_scope_opportunities_reachable(matrix):
    """Under I0 (no controls) every in-scope opportunity is reachable by construction."""
    for entry in matrix["i0_reachability"]:
        assert entry["reachable_under_I0"] is True, entry["scenario"]
        assert len(entry["blocking_controls_absent"]) >= 1
        assert entry["opportunity"] != ""


def test_i0_matrix_defers_out_of_scope_explicitly(matrix):
    """The 4 Paper-05 scenarios outside manifest scope must be deferred explicitly, not dropped."""
    deferred = matrix["out_of_manifest_scope"][0]["scenarios"]
    assert set(deferred) == {
        "Revocation Race",
        "Partitioned Revocation",
        "Budget Laundering",
        "Topology Explosion",
    }


def test_i0_matrix_asserts_no_empirical_conclusions(matrix):
    assert "No execution" in matrix["_freeze_notice"]
    assert "no empirical conclusions" in matrix["_freeze_notice"]
