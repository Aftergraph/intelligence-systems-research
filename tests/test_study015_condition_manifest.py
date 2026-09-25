import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "study015_condition_manifest.json"


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_condition_ids_are_unique_and_complete():
    doc = load_manifest()
    ids = [row["id"] for row in doc["conditions"]]
    assert len(ids) == len(set(ids))
    assert ids == [f"S{i}" for i in range(10)] + ["FULL"]


def test_all_enabled_mechanisms_are_registered():
    doc = load_manifest()
    known = set(doc["mechanisms"])
    for row in doc["conditions"]:
        assert set(row["enabled"]) <= known


def test_cumulative_ladder_is_monotonic():
    doc = load_manifest()
    rows = {row["id"]: set(row["enabled"]) for row in doc["conditions"]}
    for index in range(1, 10):
        previous = rows[f"S{index - 1}"]
        current = rows[f"S{index}"]
        assert previous < current, f"S{index} must strictly add at least one mechanism"
    assert rows["FULL"] == rows["S9"]


def test_s2_introduces_both_authority_and_runtime_revalidation():
    rows = {row["id"]: set(row["enabled"]) for row in load_manifest()["conditions"]}
    assert "authority_admission" in rows["S2"]
    assert "trust_revalidation" in rows["S2"]
    assert "authority_admission" not in rows["S1"]
    assert "trust_revalidation" not in rows["S1"]


def test_verification_precedes_recovery_and_learning():
    rows = {row["id"]: set(row["enabled"]) for row in load_manifest()["conditions"]}
    assert "independent_verification" in rows["S3"]
    assert "governed_recovery" not in rows["S3"]
    assert "governed_recovery" in rows["S5"]
    assert "governed_learning_proposals" not in rows["S7"]
    assert "governed_learning_proposals" in rows["S8"]


def test_promotion_is_last_cumulative_mechanism():
    rows = {row["id"]: set(row["enabled"]) for row in load_manifest()["conditions"]}
    assert "promotion_gates" not in rows["S8"]
    assert "promotion_gates" in rows["S9"]


def test_isolation_rules_cover_learning_state_and_matched_inputs():
    rules = " ".join(load_manifest()["isolation_rules"]).lower()
    assert "provider" in rules and "model" in rules and "workload" in rules
    assert "learning/performance stores" in rules
    assert "disabled mechanisms" in rules
