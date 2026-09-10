"""G12-5: verifier-pin tests for ICT-EXP-001 (Issue #52).

Asserts the frozen verifier pin (data/study012_verifier_pin.json) is intact
AND that the pinned class exists with the pinned contract. Static checks only.
No execution of confirmatory workloads, no empirical conclusions.
"""
import hashlib
import inspect
import json
import os
import sys
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

PIN = Path(workspace) / "data" / "study012_verifier_pin.json"
PIN_SHA = Path(workspace) / "data" / "study012_verifier_pin.json.sha256"


@pytest.fixture
def pin():
    with open(PIN) as f:
        return json.load(f)


def test_pin_sha256_matches():
    h = hashlib.sha256()
    with open(PIN, "rb") as f:
        h.update(f.read())
    assert h.hexdigest() == PIN_SHA.read_text().strip()


def test_pin_gate_identity(pin):
    assert pin["gate"].startswith("G12-5")
    assert pin["experiment_id"] == "ICT-EXP-001"
    assert pin["freeze_version"] == "DRAFT"


def test_pinned_verifier_class_importable(pin):
    import importlib

    mod = importlib.import_module("src.sdc_b0.green_verifier")
    cls = getattr(mod, pin["pinned_verifier"]["class"])
    assert inspect.isclass(cls)


def test_pinned_verify_signature(pin):
    import importlib
    import inspect as _inspect

    mod = importlib.import_module("src.sdc_b0.green_verifier")
    cls = getattr(mod, pin["pinned_verifier"]["class"])
    params = list(_inspect.signature(cls.verify).parameters)
    for expected in ("candidate_branch", "base_sha", "head_sha"):
        assert expected in params, f"verify() missing {expected}"


def test_pinned_verifier_never_imports_sandbox():
    import re

    src = (Path(workspace) / "src" / "sdc_b0" / "green_verifier.py").read_text()
    code_lines = [
        line for line in src.splitlines()
        if line.strip() and not line.strip().startswith(("#", '"""', "'''", "-", "*"))
    ]
    imports = [l for l in code_lines if re.match(r"\s*(import|from)\s+\S*worker_sandbox", l)]
    assert imports == [], f"sandbox imports found: {imports}"


def test_no_empirical_conclusions(pin):
    assert "No execution" in pin["_freeze_notice"]
    assert "no empirical conclusions" in pin["_freeze_notice"]
