import hashlib
import json
from pathlib import Path

import pytest

from experiments.study015.probe_bundle import ProbeBundleError, validate_bundle
from experiments.study015.probe_fabric import load_json

ROOT = Path(__file__).resolve().parents[1]
TARGETS = load_json(ROOT / "data" / "study015_probe_targets.draft.json")["targets"]


def make_bundle(tmp_path: Path):
    entries = []
    for i, target in enumerate(TARGETS, start=1):
        receipt = {
            "schema": "study015.probe/1.0",
            "component": target["component"],
            "source_head": target["expected_head"],
            "execution_class": "LOCAL_IMPLEMENTATION_PROBE",
            "network_used": False,
            "mechanisms": {name: True for name in target["required_mechanisms"]},
            "observations": {"fixture": True},
        }
        name = f"{target['component']}.json"
        path = tmp_path / name
        path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
        entries.append({
            "component": target["component"],
            "repository": target["repository"],
            "source_head": target["expected_head"],
            "workflow_run_id": 1000 + i,
            "artifact_id": 2000 + i,
            "artifact_name": f"fixture-{target['component']}",
            "artifact_digest": "sha256:" + ("%064x" % i),
            "receipt_path": name,
            "receipt_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    index = {
        "schema": "study015.probe-bundle-index/1.0",
        "study_id": "STUDY-015",
        "receipts": entries,
    }
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return index_path


def test_current_exact_head_bundle_validates():
    out = validate_bundle()
    assert out["component_count"] == 5
    assert len(out["probe_root_sha256"]) == 64
    assert set(out["artifact_provenance"]) == {t["component"] for t in TARGETS}


def test_valid_synthetic_bundle_composes_all_exact_heads(tmp_path):
    out = validate_bundle(make_bundle(tmp_path))
    assert out["component_count"] == len(TARGETS)
    assert len(out["probe_root_sha256"]) == 64


def test_mutated_receipt_fails_sha_binding(tmp_path):
    index_path = make_bundle(tmp_path)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    receipt = tmp_path / index["receipts"][0]["receipt_path"]
    receipt.write_text(receipt.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ProbeBundleError, match="receipt SHA mismatch"):
        validate_bundle(index_path)


def test_wrong_source_head_fails_closed(tmp_path):
    index_path = make_bundle(tmp_path)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["receipts"][0]["source_head"] = "f" * 40
    index_path.write_text(json.dumps(index) + "\n", encoding="utf-8")
    with pytest.raises(ProbeBundleError, match="source-head mismatch"):
        validate_bundle(index_path)
