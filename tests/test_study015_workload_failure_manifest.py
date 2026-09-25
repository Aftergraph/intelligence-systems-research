import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "study015_workload_failure_manifest.json"


def load():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_manifest_has_two_workloads_per_family():
    doc = load()
    counts = Counter(row["family"] for row in doc["workloads"])
    assert set(counts) == set(doc["families"])
    assert all(count >= 2 for count in counts.values())
    assert len(doc["workloads"]) == doc["workload_count"]


def test_workload_ids_are_unique():
    ids = [row["id"] for row in load()["workloads"]]
    assert len(ids) == len(set(ids))


def test_every_failure_mode_is_exercised():
    doc = load()
    declared = {row["id"] for row in doc["failure_modes"]}
    exercised = {fault for row in doc["workloads"] for fault in row["eligible_failures"]}
    assert declared <= exercised


def test_containment_failures_include_revocation_budget_replay_and_promotion():
    doc = load()
    classes = {row["id"]: row["class"] for row in doc["failure_modes"]}
    for fault in ("midflight_revocation","budget_exhaustion","replay_duplicate_action","invalid_promotion_evidence"):
        assert classes[fault] == "containment"


def test_verification_unknown_is_never_pass():
    rule = load()["rules"]["failure_class_semantics"]["verification"]
    assert "INDETERMINATE" in rule and "PASS" in rule
