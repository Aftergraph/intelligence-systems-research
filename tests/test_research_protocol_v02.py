"""Contract tests for Research Protocol v0.2."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTOCOL = ROOT / "02-RESEARCH-PROTOCOL-v0.2.md"

def _text():
    assert PROTOCOL.is_file(), "Research Protocol v0.2 is missing"
    return PROTOCOL.read_text(encoding="utf-8")

def test_r1_grounded_verification_is_fail_closed_against_judge_only_verified():
    text = _text()
    assert "ISE-R1 — Grounded verification" in text
    assert "MUST NOT be the sole basis for VERIFIED" in text
    assert "deterministic state/effect checks" in text
    assert "Agreement among judges does not establish construct validity" in text

def test_r2_pins_required_long_horizon_falsification_families():
    text = _text()
    required = [
        "stale state or stale facts", "revocation and revoked-memory reuse",
        "contradictory updates/evidence", "cross-user or cross-tenant isolation",
        "constraint decay", "replay/duplicate effects", "crash/recovery",
        "misleading or adversarial task evidence",
    ]
    for item in required:
        assert item in text, f"missing R2 falsification family: {item}"
    assert "NOT_APPLICABLE" in text

def test_r3_forbids_activity_as_scientific_progress():
    text = _text()
    assert "ISE-R3 — Verified research progress" in text
    assert "Activity MUST NOT be reported as scientific progress" in text
    for denominator in ["tokens", "wall-clock time", "financial cost", "human interventions"]:
        assert denominator in text

def test_execution_research_boundary_does_not_create_parallel_truth_plane():
    text = _text()
    assert "does not create a new Aftergraph execution plane" in text
    assert "Execution -> Evidence -> Verification -> Verified Outcome" in text
    assert "do not replace WORKS execution truth or Sentinel/domain-verifier verdicts" in text

def test_external_sources_are_motivators_not_local_replication_claims():
    text = _text()
    for arxiv_id in ["2609.12191", "2609.14976", "2609.19140"]:
        assert arxiv_id in text
    assert "not promoted into local E5/E6 evidence without independent reproduction" in text
