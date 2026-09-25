import copy
import json
from pathlib import Path

import pytest

from experiments.study015.probe_fabric import (
    ProbeFabricError,
    compose,
    composition_root,
    validate_receipt,
)

ROOT = Path(__file__).resolve().parents[1]
TARGETS = json.loads(
    (ROOT / "data" / "study015_probe_targets.draft.json").read_text(encoding="utf-8")
)["targets"]


def receipt_for(target):
    return {
        "schema": "study015.probe/1.0",
        "component": target["component"],
        "source_head": target["expected_head"],
        "execution_class": "LOCAL_IMPLEMENTATION_PROBE",
        "network_used": False,
        "mechanisms": {name: True for name in target["required_mechanisms"]},
        "observations": {"fixture": True},
    }


def test_all_target_heads_are_exact_git_shas_and_components_unique():
    components = [target["component"] for target in TARGETS]
    assert len(components) == len(set(components))
    for target in TARGETS:
        assert len(target["expected_head"]) == 40
        assert set(target["expected_head"]) <= set("0123456789abcdef")


def test_receipts_validate_against_target_mechanism_contracts():
    for target in TARGETS:
        assert validate_receipt(receipt_for(target), target=target)["component"] == target["component"]


def test_source_head_mismatch_fails_closed():
    target = TARGETS[0]
    receipt = receipt_for(target)
    receipt["source_head"] = "f" * 40
    with pytest.raises(ProbeFabricError, match="source-head mismatch"):
        validate_receipt(receipt, target=target)


def test_missing_required_mechanism_fails_closed():
    target = TARGETS[0]
    receipt = receipt_for(target)
    receipt["mechanisms"][target["required_mechanisms"][0]] = False
    with pytest.raises(ProbeFabricError, match="required mechanisms"):
        validate_receipt(receipt, target=target)


def test_composition_root_is_order_independent():
    receipts = [receipt_for(target) for target in TARGETS]
    assert composition_root(receipts) == composition_root(list(reversed(receipts)))


def test_composition_receipt_binds_all_component_heads():
    receipts = [receipt_for(target) for target in TARGETS]
    out = compose(receipts)
    assert out["schema"] == "study015.composition-probe/1.0"
    assert out["component_count"] == len(TARGETS)
    assert len(out["probe_root_sha256"]) == 64
    assert out["source_heads"] == {
        target["component"]: target["expected_head"] for target in sorted(TARGETS, key=lambda x: x["component"])
    }
