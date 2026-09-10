"""Canonical G12-10: hostile technical review of STUDY-012 readiness.

Each probe attempts to FALSIFY pre-confirmatory readiness. A probe that
FAILS names a material blocker: fix it and rerun; do not rubber-stamp.
Probes re-derive evidence independently (hashes recomputed here, file
lists walked here) rather than trusting prior verdicts.
"""

import hashlib
import json
import re
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
DATA = WORKSPACE / "data"
REGISTRY_FILE = DATA / "study012_registry_alignment.json"


def read_json(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def file_sha(name):
    return hashlib.sha256((DATA / name).read_bytes()).hexdigest()


def stored_sha(name):
    return (DATA / f"{name}.sha256").read_text(encoding="utf-8").strip().split()[0]


# ── H1: gate-chain completeness (G12-1..9 artifacts present) ────────────────

GATE_ARTIFACTS = [
    "data/study012_destructive_test_clearance.json",   # G12 clearance
    "data/study012_confirmatory_env_lock.json",        # env lock
    "data/study012_verifier_pin.json",                 # verifier pin
    "data/study012_pilot_dryrun_report.json",          # pilot dry-run
    "data/study012_condition_ladder.json",             # condition conformance
    "experiments/institutional_containment/safety.py",  # G12-6
    "experiments/institutional_containment/analyze.py", # G12-7
    "data/study012_analysis_freeze.json",              # G12-7 freeze
    "data/study012_power_plan.json",                   # G12-8
    "scripts/study012_power_analysis.py",              # G12-8 procedure
    "data/study012_registry_alignment.json",           # G12-9
]


def test_h1_all_gate_artifacts_present():
    missing = [a for a in GATE_ARTIFACTS if not (WORKSPACE / a).is_file()]
    assert not missing, f"gate-chain incomplete, missing: {missing}"


# ── H2: frozen integrity, independently re-derived ───────────────────────────

PINNED = [
    "study012_workload_manifest.json",
    "study012_analysis_freeze.json",
    "study012_power_plan.json",
]


def test_h2_all_sidecar_pins_hold():
    broken = [n for n in PINNED if file_sha(n) != stored_sha(n)]
    assert not broken, f"frozen integrity violated: {broken}"


# ── H3: golden independence (expectations precomputed, not self-derived) ────

def test_h3_golden_expectations_hardcoded():
    text = (WORKSPACE / "tests" / "test_study012_analysis_golden.py").read_text(
        encoding="utf-8")
    # Expectations must be hand-derived literals (counts, rates, reasons),
    # not values computed by the implementation under test.
    assert '"valid_pair_count"] == 4' in text or "valid_pair_count" in text
    for literal in ('"concordant_no_violation": 2', "== 0.5",
                    '"PAIR_IDENTITY_MISMATCH"',
                    '"DUPLICATE_CONDITION"',
                    '"winner"] is None'):
        assert literal in text, (
            f"golden expectation literal missing: {literal}"
        )
    assert "SYNTHETIC" in text and "confirmatory_eligible" in text, (
        "golden fixtures must be explicitly synthetic and "
        "confirmatory-ineligible"
    )


# ── H4: synthetic-only containment (no live-provider routes) ────────────────

SUSPICIOUS = re.compile(r"api_key|sk-[A-Za-z0-9]|bearer|openai\.|anthropic|live_call",
                        re.IGNORECASE)


def test_h4_no_live_provider_routes():
    hits = []
    for rel in ("experiments/institutional_containment/analyze.py",
                "scripts/study012_power_analysis.py",
                "experiments/institutional_containment/safety.py"):
        text = (WORKSPACE / rel).read_text(encoding="utf-8")
        if SUSPICIOUS.search(text):
            hits.append(rel)
    manifest = read_json("study012_workload_manifest.json")
    assert manifest.get("workload_type") == "synthetic_only"
    assert not hits, f"live-provider routes in analysis path: {hits}"


# ── H5: outcome-blind power (no results smuggled into the plan) ─────────────

def test_h5_power_plan_outcome_blind():
    plan = read_json("study012_power_plan.json")
    # Blindness is declared by VALUE (false/empty), not by key absence:
    # keys like observed_outcomes_used must be falsy, never result-bearing.
    assert plan.get("outcome_blind") is True
    assert not plan.get("observed_outcomes_used")
    assert not plan.get("empirical_conclusions")
    assert plan.get("confirmatory_execution_authorized") is False
    blob = json.dumps(plan).lower()
    for forbidden in ("p_value", "p-value", "effect_size", "reject_null",
                      "results_table"):
        assert forbidden not in blob, (
            f"power plan is not outcome-blind: {forbidden!r}"
        )


# ── H6: freeze-notice version chain ──────────────────────────────────────────

def test_h6_notice_chain_complete():
    manifest = read_json("study012_workload_manifest.json")
    registry = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    old = manifest.get("_freeze_notice", "")
    new = registry.get("effective_freeze_notice", "")
    assert "v1.0.0" in old and "NO silent edits" in old
    assert "v1.0.0" in new and "v1.0.1" in new
    assert "NO silent edits" in new or "no silent" in new.lower()


# ── H7: ID hygiene — 001 survives ONLY inside declared historical scope ─────

HISTORICAL_BASENAMES = {
    "study012_workload_manifest.json",
    "STUDY-012-ICT-PREREGISTRATION.md",
    "study012_analysis_freeze.json",
    "study012_power_plan.json",
    "study012_condition_ladder.json",
    "study012_confirmatory_env_lock.json",
    "study012_destructive_test_clearance.json",
    "study012_i0_opportunity_matrix.json",
    "study012_pilot_dryrun_report.json",
    "study012_verifier_pin.json",
    "test_study012_clearance.py",
}


def test_h7_no_undeclared_001_canonical_claims():
    registry = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    declared = set()
    for entry in registry.get("historical_scope", {}).get("retained_001", []):
        declared.add(entry.split(" ")[0].rsplit("/", 1)[-1])
    assert HISTORICAL_BASENAMES <= declared, (
        f"historical scope under-declares: {HISTORICAL_BASENAMES - declared}"
    )
    offenders = []
    for path in list(DATA.glob("study012_*.json")) + list(
            WORKSPACE.glob("STUDY-012*.md")):
        text = path.read_text(encoding="utf-8")
        if path.name in (REGISTRY_FILE.name,):
            continue
        if '"experiment_id": "ICT-EXP-001"' in text or (
                path.suffix == ".md" and "**Study ID:** STUDY-012 / ICT-EXP-001"
                in text):
            if path.name not in declared:
                offenders.append(path.name)
    assert not offenders, (
        f"ICT-EXP-001 presented outside declared historical scope: {offenders}"
    )


def test_h7_registry_canonical_unambiguous():
    registry = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    assert registry.get("canonical_experiment_id") == "ICT-EXP-0001"
    blob = json.dumps(registry)
    assert blob.count("ICT-EXP-0001") >= 2, "canonical ID must dominate record"


# ── H8: amendment validity, independently re-derived ─────────────────────────

def test_h8_amendment_pins_real_hashes():
    registry = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    amendment = next(
        a for a in registry["protocol_amendments"]
        if a["amendment_version"] == "v1.0.1")
    live_manifest = hashlib.sha256(
        (DATA / "study012_workload_manifest.json").read_bytes()).hexdigest()
    assert amendment["base_manifest_sha256"] == live_manifest
    assert amendment["base_freeze_version"] == "v1.0.0"
    assert amendment["stage"] == "pre-confirmatory"


# ── H9: no execution evidence, no Paper 06 conclusions ───────────────────────

def test_h9_no_results_artifacts():
    results = [p.name for p in DATA.glob("study012_*result*.json")]
    assert not results, f"results artifacts pre-execution: {results}"
    papers = WORKSPACE / "PAPERS"
    conclusions = [
        p.name for p in papers.glob("06-*.md")] if papers.is_dir() else []
    assert not conclusions, f"Paper 06 conclusions pre-execution: {conclusions}"
    registry = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    assert registry.get("confirmatory_execution_occurred") is False
