import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator

from experiments.system_one_acceleration.corpus import build_calibration_corpus
from experiments.system_one_acceleration.jar15_dataset import (
    build_prospective_dataset,
    build_split_manifest,
    canonical_sha256,
    dataset_document,
    semantic_case_hash,
)

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "jar_exp_0015_dataset_v01.json"
MANIFEST_PATH = ROOT / "data" / "jar_exp_0015_split_manifest_v01.json"
DATASET_SCHEMA = ROOT / "schemas" / "jar-exp-0015-dataset.v0.1.json"
MANIFEST_SCHEMA = ROOT / "schemas" / "jar-exp-0015-split-manifest.v0.1.json"

FROZEN_DATASET_SHA256 = "de90286586397af21a568a91c4cd4ec4d56ccfd8a7db09fbd2d7167f6541fac9"
FROZEN_MANIFEST_SHA256 = "185f5ca9ed25286fb3c60092f83357e0493038338b08bbdd9b4251c9f01707d1"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_frozen_dataset_and_manifest_hashes_are_exact():
    assert hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest() == FROZEN_DATASET_SHA256
    assert hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest() == FROZEN_MANIFEST_SHA256


def test_frozen_files_match_deterministic_generator_exactly():
    assert _load(DATASET_PATH) == dataset_document()
    assert _load(MANIFEST_PATH) == build_split_manifest()


def test_frozen_dataset_and_manifest_validate_against_schemas():
    Draft202012Validator(_load(DATASET_SCHEMA)).validate(_load(DATASET_PATH))
    Draft202012Validator(_load(MANIFEST_SCHEMA)).validate(_load(MANIFEST_PATH))


def test_split_math_is_exact_per_decision_type():
    rows = _load(DATASET_PATH)["cases"]
    assert len(rows) == 320
    assert Counter(row["split"] for row in rows) == {
        "calibration": 192,
        "holdout": 128,
    }
    by_type = defaultdict(Counter)
    for row in rows:
        by_type[row["decision_type"]][row["split"]] += 1
    assert len(by_type) == 8
    for counts in by_type.values():
        assert counts == {"calibration": 24, "holdout": 16}


def test_case_ids_and_semantic_hashes_are_unique():
    rows = _load(DATASET_PATH)["cases"]
    ids = [row["case_id"] for row in rows]
    assert len(ids) == len(set(ids)) == 320

    hashes = [
        semantic_case_hash(
            decision_type=row["decision_type"],
            state=row["state"],
            expected=row["expected"],
            critical=row["critical"],
        )
        for row in rows
    ]
    assert len(hashes) == len(set(hashes)) == 320


def test_no_exact_semantic_duplicate_of_parent_calibration_corpus():
    parent_hashes = {
        semantic_case_hash(
            decision_type=row.decision_type,
            state=row.state,
            expected=row.expected,
            critical=row.critical,
        )
        for row in build_calibration_corpus()
    }
    child_hashes = {
        semantic_case_hash(
            decision_type=row.decision_type,
            state=row.state,
            expected=row.expected,
            critical=row.critical,
        )
        for row in build_prospective_dataset()
    }
    assert len(parent_hashes) == 158
    assert len(child_hashes) == 320
    assert parent_hashes.isdisjoint(child_hashes)


def test_authority_sensitive_classes_have_required_critical_coverage():
    rows = _load(DATASET_PATH)["cases"]
    for decision_type in ("needs_human", "risk_level"):
        critical = [
            row for row in rows
            if row["decision_type"] == decision_type and row["critical"]
        ]
        assert len(critical) >= 8
        assert any(row["split"] == "calibration" for row in critical)
        assert any(row["split"] == "holdout" for row in critical)


def test_holdout_membership_is_bound_in_manifest_without_labels_or_state():
    dataset = {row["case_id"]: row for row in _load(DATASET_PATH)["cases"]}
    manifest = _load(MANIFEST_PATH)
    assert manifest["exact_parent_duplicates"] == 0
    assert manifest["parent_case_count_checked"] == 158
    assert manifest["case_count"] == 320
    for entry in manifest["cases"]:
        row = dataset[entry["case_id"]]
        assert entry["split"] == row["split"]
        assert entry["critical"] == row["critical"]
        assert "expected" not in entry
        assert "state" not in entry
        assert entry["semantic_sha256"] == semantic_case_hash(
            decision_type=row["decision_type"],
            state=row["state"],
            expected=row["expected"],
            critical=row["critical"],
        )


def test_dataset_document_hash_changes_if_holdout_label_or_state_mutates():
    dataset = _load(DATASET_PATH)
    original = canonical_sha256(dataset)
    candidate = json.loads(json.dumps(dataset))
    holdout = next(row for row in candidate["cases"] if row["split"] == "holdout")
    holdout["state"]["signal"] += "-tampered"
    assert canonical_sha256(candidate) != original
