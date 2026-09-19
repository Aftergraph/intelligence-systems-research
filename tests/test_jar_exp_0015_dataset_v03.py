import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator

from experiments.system_one_acceleration.corpus import build_calibration_corpus
from experiments.system_one_acceleration.jar15_dataset import semantic_case_hash
from experiments.system_one_acceleration.jar15_dataset_v03 import (
    build_prospective_dataset_v03,
    dataset_document_v03,
    split_manifest_v03,
)
from experiments.system_one_acceleration.state_projection import project_decision_state

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "jar_exp_0015_dataset_v03.json"
MANIFEST = ROOT / "data" / "jar_exp_0015_split_manifest_v03.json"
DATASET_SCHEMA = ROOT / "schemas" / "jar-exp-0015-dataset.v0.3.json"
MANIFEST_SCHEMA = ROOT / "schemas" / "jar-exp-0015-split-manifest.v0.3.json"

DATASET_SHA = "51846d8b4a95540a8e182a823a7256fbdd69d61b3244f89e078db77ad7e0496e"
MANIFEST_SHA = "46b0123ed31b27d80823e518bef9e24bf4f1cc672f763d7b75e446698a00b745"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_v03_hashes_are_frozen():
    assert hashlib.sha256(DATASET.read_bytes()).hexdigest() == DATASET_SHA
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == MANIFEST_SHA


def test_v03_frozen_files_match_generator_exactly():
    assert _load(DATASET) == dataset_document_v03()
    assert _load(MANIFEST) == split_manifest_v03()


def test_v03_schemas_validate_frozen_files():
    Draft202012Validator(_load(DATASET_SCHEMA)).validate(_load(DATASET))
    Draft202012Validator(_load(MANIFEST_SCHEMA)).validate(_load(MANIFEST))


def test_v03_split_math_is_exact():
    rows = _load(DATASET)["cases"]
    assert len(rows) == 3904
    assert Counter(row["split"] for row in rows) == {"calibration": 1952, "holdout": 1952}
    by_type = defaultdict(Counter)
    for row in rows:
        by_type[row["decision_type"]][row["split"]] += 1
    assert len(by_type) == 8
    assert all(c == {"calibration": 244, "holdout": 244} for c in by_type.values())


def test_v03_projection_preserves_all_provider_semantics_exactly():
    for row in _load(DATASET)["cases"]:
        assert set(row["state"]) == {"scenario"}
        projected = project_decision_state(
            decision_type=row["decision_type"], state=row["state"]
        )
        assert projected == row["state"]
        assert len(projected["scenario"]) >= 80


def test_v03_route_labels_are_not_verbatim_in_provider_input():
    for row in _load(DATASET)["cases"]:
        if row["decision_type"] not in {"route_model", "route_tool_family"}:
            continue
        assert str(row["expected"]).lower() not in row["state"]["scenario"].lower()


def test_v03_ids_semantics_and_parent_separation():
    rows = _load(DATASET)["cases"]
    assert len({row["case_id"] for row in rows}) == 3904
    child = {
        semantic_case_hash(
            decision_type=row["decision_type"],
            state=row["state"],
            expected=row["expected"],
            critical=row["critical"],
        )
        for row in rows
    }
    parent = {
        semantic_case_hash(
            decision_type=row.decision_type,
            state=row.state,
            expected=row.expected,
            critical=row.critical,
        )
        for row in build_calibration_corpus()
    }
    assert len(child) == 3904
    assert len(parent) == 158
    assert child.isdisjoint(parent)


def test_v03_manifest_hides_labels_and_state_and_binds_semantics():
    dataset = {row["case_id"]: row for row in _load(DATASET)["cases"]}
    manifest = _load(MANIFEST)
    assert manifest["exact_parent_duplicates"] == 0
    assert manifest["case_count"] == 3904
    for entry in manifest["cases"]:
        assert "expected" not in entry
        assert "state" not in entry
        row = dataset[entry["case_id"]]
        assert entry["semantic_sha256"] == semantic_case_hash(
            decision_type=row["decision_type"],
            state=row["state"],
            expected=row["expected"],
            critical=row["critical"],
        )
