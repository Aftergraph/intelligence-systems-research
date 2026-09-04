"""
test_verifier_v2_validation.py
==============================

Pre-run gate blocker #6 (verifier validation): pins the layered
verifier v2.0.0 against the 20 frozen workloads:
- synthetic-correct responses pass on all 20
- failure responses are rejected on all 20
- KEYWORD-correct but decision-wrong responses are REJECTED
  (the semantic upgrade's core claim: the study must not primarily
  measure keyword matching quality)
- receipt binding: verifier_version + response_hash in every receipt
"""

import json
import os
import sys
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

sys.path.insert(0, str(Path(workspace) / "experiments" / "live_benchmark"))

from verifier_v2 import (
    VERIFIER_VERSION,
    keyword_layer,
    structured_layer,
    verdict_section_layer,
    verify_candidate_completion,
)


@pytest.fixture(scope="module")
def workloads():
    rich = json.load(open(Path(workspace) / "data" / "study011_workloads_frozen.json",
                          encoding="utf-8"))
    assert len(rich["workloads"]) == 20
    return rich["workloads"]


def synth_good(w):
    """Build a response that genuinely satisfies the frozen contract:
    fixture decisions stated, derived arithmetic values stated, VERDICT
    section, all required keywords."""
    ac = w["acceptance_criteria"]["required_output_contains"]
    lines = []
    fx = (w.get("inputs") or {}).get("fixtures", {})
    dec = fx.get("decision")
    if isinstance(dec, dict):
        for cap, d in dec.items():
            lines.append(f"{cap}: {d}")
    elif isinstance(dec, str):
        lines.append(f"decision: {dec}")
    if "ledger_P" in fx:
        p = sum(float(x) for x in fx["ledger_P"])
        q = sum(float(x) for x in fx["ledger_Q"])
        lines.append(f"ledger delta: {round(p - q, 2):.2f}")
        if fx.get("reconciled_total") is not None:
            lines.append(f"reconciled total: {float(fx['reconciled_total']):.2f}")
    if "costs" in fx:
        total = sum(float(v) for v in fx["costs"].values())
        lines.append(f"total: {total:.2f}")
        if "remaining" in fx:
            lines.append(f"remaining: {float(fx['remaining']):.2f}")
    if fx.get("sum") is not None:
        lines.append(f"sum: {float(fx['sum']):.2f}")
    lines.append("VERDICT")
    lines.extend(ac)
    return "\n".join(lines)


def test_synthetic_good_passes_all_20(workloads):
    n = sum(1 for w in workloads if verify_candidate_completion(synth_good(w), w)["pass"])
    assert n == 20, f"synthetic-correct pass rate {n}/20"


def test_failure_rejected_all_20(workloads):
    n = sum(1 for w in workloads
            if not verify_candidate_completion("I cannot complete this task.", w)["pass"])
    assert n == 20


def test_keyword_satisfying_wrong_decisions_rejected(workloads):
    """THE semantic-upgrade acceptance test: a response that contains all
    required keywords but states the WRONG fixture decisions must be
    rejected. The v1 keyword-only verifier would PASS this response."""
    rejected = 0
    checked = 0
    for w in workloads:
        fx = (w.get("inputs") or {}).get("fixtures", {})
        dec = fx.get("decision")
        if not isinstance(dec, dict):
            continue
        checked += 1
        inverted = "\n".join(f"{cap}: {'DENY' if str(d).upper().startswith('ALLOW') else 'ALLOW'}"
                             for cap, d in dec.items())
        lying = (inverted + "\nVERDICT\n"
                 + "\n".join(w["acceptance_criteria"]["required_output_contains"]))
        assert not verify_candidate_completion(lying, w)["pass"], (
            f"{w['workload_id']}: keyword-correct but decision-wrong response was ACCEPTED. "
            f"The verifier would measure keyword matching, not decision correctness."
        )
    assert checked >= 1, f"expected >=1 decision-map workload, got {checked}"


def test_layers_independent(workloads):
    """Each layer must be independently observable in the result."""
    w = workloads[0]
    r = verify_candidate_completion(synth_good(w), w)
    assert set(r["layers"]) == {"keywords", "structured", "verdict_section"}
    assert r["verifier_version"] == "2.0.0"


def test_receipt_hash_binds_response_and_verdict(workloads):
    w = workloads[0]
    r1 = verify_candidate_completion(synth_good(w), w)
    r2 = verify_candidate_completion(synth_good(w), w)
    r3 = verify_candidate_completion(synth_good(w) + "\nextra", w)
    assert r1["receipt_hash"] == r2["receipt_hash"]  # deterministic
    assert r1["receipt_hash"] != r3["receipt_hash"]  # response-bound


def test_keyword_layer_unchanged_semantics(workloads):
    """L1 must behave exactly like the v1 verifier (frozen prereg semantics)."""
    w = workloads[0]
    required = w["acceptance_criteria"]["required_output_contains"]
    ok, missing = keyword_layer("\n".join(required), w)
    assert ok and not missing
    ok2, missing2 = keyword_layer("nothing relevant here", w)
    assert not ok2 and set(missing2) == set(required)


def test_all_20_workloads_have_checkable_fixtures(workloads):
    """The structured layer requires frozen fixtures; all 20 workloads
    must carry them (this is what makes v2 possible)."""
    n = sum(1 for w in workloads
            if isinstance((w.get("inputs") or {}).get("fixtures"), dict))
    assert n == 20
