import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator

from experiments.system_one_acceleration.corpus import build_calibration_corpus
from experiments.system_one_acceleration.jar15_dataset import semantic_case_hash
from experiments.system_one_acceleration.jar15_dataset_v02 import (
    CALIBRATION_PER_TYPE,
    HOLDOUT_PER_TYPE,
    TOTAL_CASES,
    build_prospective_dataset_v02,
    dataset_document_v02,
    split_manifest_v02,
)

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "jar_exp_0015_dataset_v02.json"
MANIFEST = ROOT / "data" / "jar_exp_0015_split_manifest_v02.json"
DATASET_SCHEMA = ROOT / "schemas" / "jar-exp-0015-dataset.v0.2.json"
MANIFEST_SCHEMA = ROOT / "schemas" / "jar-exp-0015-split-manifest.v0.2.json"

DATASET_SHA = "690a28874f409a7624d371374637c0421ef6008179eba68fdc8a02a8d539bc9d"
MANIFEST_SHA = "9821b7513dee79d092ffd999e4848099c8b676529687b689b573ce02e5093dac"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_v02_hashes_are_frozen():
    assert hashlib.sha256(DATASET.read_bytes()).hexdigest() == DATASET_SHA
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == MANIFEST_SHA


def test_v02_frozen_files_match_generator_exactly():
    assert _load(DATASET) == dataset_document_v02()
    assert _load(MANIFEST) == split_manifest_v02()


def test_v02_schemas_validate_frozen_files():
    Draft202012Validator(_load(DATASET_SCHEMA)).validate(_load(DATASET))
    Draft202012Validator(_load(MANIFEST_SCHEMA)).validate(_load(MANIFEST))


def test_v02_split_math_is_exact():
    rows = _load(DATASET)["cases"]
    assert len(rows) == TOTAL_CASES == 3904
    assert Counter(row["split"] for row in rows) == {
        "calibration": 1952,
        "holdout": 1952,
    }
    by_type = defaultdict(Counter)
    for row in rows:
        by_type[row["decision_type"]][row["split"]] += 1
    assert len(by_type) == 8
    for counts in by_type.values():
        assert counts == {
            "calibration": CALIBRATION_PER_TYPE,
            "holdout": HOLDOUT_PER_TYPE,
        }


def test_v02_ids_and_semantic_hashes_are_unique():
    rows = _load(DATASET)["cases"]
    ids = [row["case_id"] for row in rows]
    assert len(ids) == len(set(ids)) == 3904
    hashes = {
        semantic_case_hash(
            decision_type=row["decision_type"],
            state=row["state"],
            expected=row["expected"],
            critical=row["critical"],
        )
        for row in rows
    }
    assert len(hashes) == 3904


def test_v02_has_no_exact_parent_duplicate():
    parent = {
        semantic_case_hash(
            decision_type=row.decision_type,
            state=row.state,
            expected=row.expected,
            critical=row.critical,
        )
        for row in build_calibration_corpus()
    }
    child = {
        semantic_case_hash(
            decision_type=row.decision_type,
            state=row.state,
            expected=row.expected,
            critical=row.critical,
        )
        for row in build_prospective_dataset_v02()
    }
    assert len(parent) == 158
    assert len(child) == 3904
    assert parent.isdisjoint(child)


def test_v02_manifest_hides_labels_and_state_but_binds_semantics():
    dataset = {row["case_id"]: row for row in _load(DATASET)["cases"]}
    manifest = _load(MANIFEST)
    assert manifest["case_count"] == 3904
    assert manifest["exact_parent_duplicates"] == 0
    for entry in manifest["cases"]:
        assert "expected" not in entry
        assert "state" not in entry
        row = dataset[entry["case_id"]]
        assert entry["split"] == row["split"]
        assert entry["semantic_sha256"] == semantic_case_hash(
            decision_type=row["decision_type"],
            state=row["state"],
            expected=row["expected"],
            critical=row["critical"],
        )


def test_v02_authority_sensitive_critical_cases_exist_in_both_splits():
    rows = _load(DATASET)["cases"]
    for dtype in ("needs_human", "risk_level"):
        critical = [r for r in rows if r["decision_type"] == dtype and r["critical"]]
        assert len(critical) >= 8
        assert {r["split"] for r in critical} == {"calibration", "holdout"}
