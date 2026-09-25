import json
from pathlib import Path

import pytest

from experiments.study015.causal_bundle import (
    CausalBundleError,
    compute_causal_root,
    validate_causal_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "study015_causal_receipts" / "current" / "index.json"


def test_current_causal_bundle_is_exact_head_bound():
    out = validate_causal_bundle()
    assert out["schema"] == "study015.causal-bundle/1.0"
    assert out["component_probe_root_sha256"] == "e9b5e00ca523a5c294406bf2c871630e75d150f65953561092ccb8ef52fd55d7"
    assert out["causal_root_sha256"] == "30e2d91a343418c34c703333d1d5a3cb5e605e6c8c926e0d6c37d010a71c56f1"
    assert all(out["seams"].values())
    assert all(out["hostile"].values())
    assert out["live_performance_claim"] is False


def test_root_is_sensitive_to_steward_receipt():
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    steward = index["steward"]
    base = compute_causal_root(
        component_probe_root_sha256=index["component_probe_root_sha256"],
        steward_source_head=steward["source_head"],
        steward_receipt_sha256=steward["receipt_sha256"],
        steward_artifact_digest=steward["artifact_digest"],
    )
    mutated = compute_causal_root(
        component_probe_root_sha256=index["component_probe_root_sha256"],
        steward_source_head=steward["source_head"],
        steward_receipt_sha256="f" * 64,
        steward_artifact_digest=steward["artifact_digest"],
    )
    assert base != mutated


def test_exact_subject_must_equal_verification_head(tmp_path):
    src = INDEX.parent
    for file in src.iterdir():
        (tmp_path / file.name).write_bytes(file.read_bytes())
    receipt_path = tmp_path / "steward-composition.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["identity"]["verification_head_sha"] = "e" * 40
    receipt_path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    import hashlib
    index["steward"]["receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    index["causal_root_sha256"] = compute_causal_root(
        component_probe_root_sha256=index["component_probe_root_sha256"],
        steward_source_head=index["steward"]["source_head"],
        steward_receipt_sha256=index["steward"]["receipt_sha256"],
        steward_artifact_digest=index["steward"]["artifact_digest"],
    )
    (tmp_path / "index.json").write_text(json.dumps(index) + "\n", encoding="utf-8")
    with pytest.raises(CausalBundleError, match="exact subject"):
        validate_causal_bundle(tmp_path / "index.json")
