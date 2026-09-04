"""
test_threat_model_binding.py
============================

Pins the binding between the threat model
(`security/THREAT-MODEL-AND-SUPPLY-CHAIN.md` SEC-001) and the
actual test functions in `security/test_security_suite.py`. The
threat model claims "tested by X" for each defense; this test
verifies that each referenced test function actually exists.

Also pins:
- Every MITRE ATLAS technique referenced in the threat model
  corresponds to a real ATLAS technique ID format (AML.Txxxx).
- The 10 STRIDE-AI threats (TH-01..TH-10) are all addressed.
"""

import ast
import os
import re
import sys
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)


THREAT_MODEL = Path(workspace) / "security" / "THREAT-MODEL-AND-SUPPLY-CHAIN.md"
SECURITY_SUITE = Path(workspace) / "security" / "test_security_suite.py"


def test_threat_model_exists():
    assert THREAT_MODEL.exists(), f"missing threat model: {THREAT_MODEL}"


def test_security_suite_exists():
    assert SECURITY_SUITE.exists(), f"missing security suite: {SECURITY_SUITE}"


def test_threat_model_covers_TH_01_through_TH_10():
    """All 10 STRIDE-AI threats must be defined."""
    text = THREAT_MODEL.read_text(encoding="utf-8")
    for i in range(1, 11):
        th_id = f"**TH-{i:02d}**"
        assert th_id in text, f"Threat model missing {th_id}"


def test_threat_model_atlas_techniques_are_well_formed():
    """All AML.Txxxx references in the threat model must match the
    ATLAS ID format."""
    text = THREAT_MODEL.read_text(encoding="utf-8")
    refs = re.findall(r"AML\.\w+", text)
    for ref in refs:
        assert re.match(r"^AML\.T\d{4}$", ref), (
            f"Bad ATLAS ID format: {ref!r}"
        )


@pytest.mark.parametrize("test_func_name", [
    "test_evidence_tampering_tier0_rejected",
    "test_unauthorized_capability_outside_scope",
    "test_delegation_purpose_mismatch_forgery",
    "test_evidence_tampering_failed_result_rejected",
    "test_budget_exhaustion_containment",
    "test_subdelegation_scope_attenuation",
])
def test_threat_model_references_existing_test(test_func_name):
    """Every test name referenced in the threat model's
    'Tested By' column must exist as a function in test_security_suite.py."""
    # AST-parse the security suite to extract function names
    src = SECURITY_SUITE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    func_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    assert test_func_name in func_names, (
        f"Threat model references {test_func_name!r} but it does not "
        f"exist in {SECURITY_SUITE.name}. Either add the test or "
        f"update the threat model."
    )


def test_threat_model_references_resolve_to_real_tests():
    """Cross-check: every test function name appearing in the threat
    model's 'Tested By' column must exist in the security suite.

    This is a stronger version of the parametrize test above: it
    parses the actual markdown table rather than a hardcoded list."""
    text = THREAT_MODEL.read_text(encoding="utf-8")
    # Match "Tested By | `test_xxx`" or "Tested By | test_xxx"
    referenced = re.findall(r"`(test_[a-zA-Z0-9_]+)`", text)
    src = SECURITY_SUITE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    func_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    for t in referenced:
        assert t in func_names, (
            f"Threat model references {t!r} which does not exist in "
            f"test_security_suite.py. Update the threat model or "
            f"add the missing test."
        )
