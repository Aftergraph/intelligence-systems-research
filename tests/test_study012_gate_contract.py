import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data" / "study012_gate_contract.json"
PREREG = ROOT / "STUDY-012-ICT-PREREGISTRATION.md"

EXPECTED = {
    "G12-1": "frozen workload/scenario manifest",
    "G12-2": "adversarial opportunity reachability under I0",
    "G12-3": "I0-I6 condition-conformance tests",
    "G12-4": "no silent simulation/fallback substitution",
    "G12-5": "independent evidence/verification authority",
    "G12-6": "synthetic-only safety boundary with no real third-party target",
    "G12-7": "frozen analysis script + golden synthetic tests",
    "G12-8": "outcome-blind power/sample-size procedure",
    "G12-9": "research registries aligned",
    "G12-10": "hostile technical review before first confirmatory look",
}


def test_gate_contract_matches_issue_52_acceptance_order():
    payload = json.loads(CONTRACT.read_text())
    assert payload["canonical_source"] == "GitHub issue #52"
    actual = {item["id"]: item["name"] for item in payload["gates"]}
    assert actual == EXPECTED


def test_prereg_names_every_canonical_gate_and_separates_supplemental_readiness():
    text = PREREG.read_text()
    assert "Canonical G12 acceptance gates" in text
    for gate_id, name in EXPECTED.items():
        assert f"{gate_id} | {name}" in text
    assert "Supplemental readiness artifacts (do not renumber or satisfy G12 gates by themselves)" in text
