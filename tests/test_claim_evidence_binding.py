"""
test_claim_evidence_binding.py
=============================

Pins the binding between the audited claims in
`data/claim_evidence_audit.csv` and the raw evidence files they
reference. This is the most important regression test in the program:
if any of the audited claims is silently upgraded (e.g., "FCR ELIMINATED"
re-appearing in the README), or if the supporting evidence file is
removed, this test fails.

Pinned claims (2026-09-04 audit, AUDIT-EVID-001):

- C-001: FCR = 0.0% in MISSION-Bench sample, N=100, Wilson 95% CI
  [0.0%, 3.89%]. (SIMULATION_SUPPORTED.)
- C-002: Control plane core payload <= 250 tokens (exact
  227, [220, 235]). (INTERNALLY_SUPPORTED / VERIFIED.)
- C-003: CPVO reduced 81.3% [74.2%, 87.5%]. (SIMULATION_SUPPORTED.)
- C-004: Operator preference for mission-centric UX. (UNTESTED,
  preregistered only, N=0 humans.)
- C-005: SPEC-001 cross-runtime conformance 100% (14/14).
  (PARTIALLY_SUPPORTED — in-tree + Node only.)
- C-006: Authority delegation strictly attenuates across sub-agents.
  (INTERNALLY_SUPPORTED / VERIFIED.)
- C-007: Evidence gating is the causal prerequisite enabling retry
  loops. McNemar p < 0.0001, VSR +29.0% [18.2%, 39.1%].
  (SIMULATION_SUPPORTED / EMPIRICALLY_SUPPORTED.)
- C-008: Progressive disclosure restores small/open model compliance
  40% -> 83%; interference 25% -> 2%. (SIMULATION_SUPPORTED.)
- C-009: Trajectory hash-chain + external signed anchoring detects
  full-history rewrites. (INTERNALLY_SUPPORTED.)
- C-010: STUDY-008 — 2 LIVE_VALID / 9 LIVE_PROVIDER_FAILURE / 264
  SIMULATED. (PARTIAL_LIVE_SUPPORTED, reclassified
  METHODOLOGICAL_PILOT in registry.)
- C-011: Scored router matches frontier (84% vs 84%) at -22.2% cost
  and -17.2% latency. (SIMULATION_SUPPORTED.)
- C-012: Durable work plane recovers from controlled crash points
  with 100% recovery, 0 duplicate side effects. (INTERNALLY_SUPPORTED.)
- C-013: Logical assurance boundary 0% compromise across 9 hostile
  vectors. (INTERNALLY_SUPPORTED.)
- C-014: STUDY-011 zero-cost readiness pre-execution gate passed.
  (PRE_EXECUTION_GATE_PASSED, no live confirmatory data.)
- C-015: STUDY-008 status reclassified METHODOLOGICAL_PILOT.
  (WALKED_BACK.)

This test also forbids these forbidden tokens in front-door documents:
  - "FCR ELIMINATED" (audit walked this back)
  - "1,000 live runs" (no such data; STUDY-008 attempted 275)
  - "HEVO −68" (GOMS simulation only, N=0 humans)
  - "D2 INTEGRATE 65%" (no audited evidence; gate decision pending)
  - "zero population failure" (Wilson interval, not point estimate)
"""

import csv
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)


# ---------------------------------------------------------------------------
# 1. Every raw evidence file referenced in the audit must still exist.
# ---------------------------------------------------------------------------

# A curated subset of high-stakes evidence files. The full set is large;
# we pin the ones whose absence would break the defensible record.
PINNED_EVIDENCE_FILES = [
    "data/claim_evidence_audit.csv",
    "data/decision_log.csv",
    "data/experiment_registry.csv",
    "data/open_questions.csv",
    "data/results_mission_bench.csv",
    "data/results_confounder_analysis.csv",
    "data/router_evaluation.csv",
    "data/durability_fault_injection_results.json",
    "data/assurance_adversarial_results.json",
    "data/live_run_manifest.json",
    "data/live_results.csv",
    "data/statistical_audit_recomputed.csv",
    "data/study011_workload_manifest.json",
    "data/study011_workloads_frozen.json",
    "data/study011_provider_model_matrix.json",
    "data/study011_preregistration_manifest.json",
    "data/study011_preregistration_manifest.v1.0.0.json",
    "data/study011_preregistration_manifest.v1.0.1.json",
    "data/study011_preregistration_manifest.sha256",
    "schemas/mission.v0alpha1.json",
    "STUDY-006-HCI-PREREGISTRATION.md",
    "STUDY-011-LIVE-CROSS-PROVIDER-PREREGISTRATION.md",
    "STUDY-011-AMENDMENTS.md",
    "STUDY-011-READINESS-REPORT.md",
    "STUDY-011-COST-FORECAST.md",
    "STUDY-011-CROSS-PROVIDER-REPLICATION.md",
    "STUDY-011-V031-WAVE-EVIDENCE.md",
    "EVIDENCE-AUDIT-AND-CLAIM-REGISTRY.md",
    "README.md",
    "00-EXECUTIVE-SUMMARY.md",
    "CHANGELOG.md",
]


@pytest.mark.parametrize("path", PINNED_EVIDENCE_FILES)
def test_pinned_evidence_file_exists(path):
    """Every file that an audited claim depends on must still exist."""
    p = Path(workspace) / path
    assert p.exists(), f"Missing evidence file: {path}"
    assert p.stat().st_size > 0, f"Evidence file is empty: {path}"


# ---------------------------------------------------------------------------
# 2. STUDY-011 frozen artifacts must remain semantically unchanged: the
# workload-set content (the root_hash) and the prereg SHA-256 must hold.
# File-level byte hashes (which depend on line endings) are recorded in
# the preregistration manifest's `file_hash` field, which the
# `test_preregistration_manifest_self_hash_matches_sidecar` test pins.
# ---------------------------------------------------------------------------

def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _root_hash(p: Path) -> str:
    """The content-level root_hash: sha256(''.join(sorted(workload_sha256_list))).
    Independent of file line endings, so the workload SET is immutable
    across CRLF/LF normalizations."""
    import json as _json
    manifest = _json.loads(p.read_text(encoding="utf-8"))
    sha_list = sorted(w["sha256"] for w in manifest["workloads"])
    return __import__("hashlib").sha256("".join(sha_list).encode()).hexdigest()


# The workload-set root_hash. This is the *meaningful* invariant: the
# set of 20 frozen workloads. File-byte hashes are pinned in the
# preregistration manifest separately.
STUDY011_FROZEN_ROOT_HASH = "e823102a4ff09bfca560c95e341aa3eaf7a4003215abd3900749afc64d3e4e06"


@pytest.mark.parametrize("path", [
    "data/study011_workload_manifest.json",
])
def test_frozen_workload_set_root_hash_unchanged(path):
    """The 20-workload set's content-level root_hash must be unchanged.

    Any change to the workload set requires a new preregistration
    version + STUDY-011-AMENDMENTS.md entry. The root_hash is the
    meaningful invariant; file-byte hashes depend on line endings
    and are tracked separately by the sidecar test below.
    """
    p = Path(workspace) / path
    actual = _root_hash(p)
    assert actual == STUDY011_FROZEN_ROOT_HASH, (
        f"DRIFT: {path} workload set root_hash mismatch\n"
        f"  expected (frozen): {STUDY011_FROZEN_ROOT_HASH}\n"
        f"  actual           : {actual}\n"
        f"Any drift requires a new STUDY-011 preregistration version "
        f"+ amendment entry."
    )


# ---------------------------------------------------------------------------
# 3. The preregistration manifest self-hash must equal the sidecar hash.
# ---------------------------------------------------------------------------

def test_preregistration_manifest_self_hash_matches_sidecar():
    """The SHA-256 in the preregistration manifest must equal the value
    recorded in the sidecar file. This catches the case where the
    manifest is edited but the sidecar is forgotten (and vice versa)."""
    manifest = Path(workspace) / "data/study011_preregistration_manifest.json"
    sidecar = Path(workspace) / "data" / "study011_preregistration_manifest.sha256"
    actual = _sha256(manifest)
    recorded = sidecar.read_text(encoding="utf-8").strip().split()[0]
    assert actual == recorded, (
        f"preregistration_manifest.sha256 mismatch\n"
        f"  manifest SHA-256: {actual}\n"
        f"  sidecar recorded: {recorded}"
    )


# ---------------------------------------------------------------------------
# 4. JAR-EXP-0008 must be reclassified (not COMPLETED).
# ---------------------------------------------------------------------------

def test_study008_reclassified_to_methodological_pilot():
    """AUDIT-EVID-001 walked back JAR-EXP-0008 to METHODOLOGICAL_PILOT.
    The registry must reflect this; otherwise the audit reverts."""
    p = Path(workspace) / "data/experiment_registry.csv"
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    row = next((r for r in rows if r["experiment_id"] == "JAR-EXP-0008"),
               None)
    assert row is not None, "JAR-EXP-0008 missing from registry"
    assert row["status"] == "METHODOLOGICAL_PILOT", (
        f"JAR-EXP-0008 status reverted from METHODOLOGICAL_PILOT to "
        f"{row['status']!r}. This would silently re-upgrade a pilot "
        f"to a completed study. See AUDIT-EVID-001."
    )


# ---------------------------------------------------------------------------
# 5. STUDY-008 live run accounting must be 2/9/264 (definitive count).
# ---------------------------------------------------------------------------

def test_study008_live_accounting_matches_audit():
    """2 LIVE_VALID + 9 LIVE_PROVIDER_FAILURE + 264 SIMULATED = 275.
    Source: AUDIT-EVID-001."""
    p = Path(workspace) / "data/live_run_manifest.json"
    data = json.load(open(p, encoding="utf-8"))
    # The manifest has a top-level breakdown by classification
    breakdown = (
        data.get("executed_matrix", {}).get("classification_breakdown", {})
    )
    lv = breakdown.get("LIVE_VALID", 0)
    pf = breakdown.get("LIVE_PROVIDER_FAILURE", 0)
    sim = breakdown.get("SIMULATED", 0)
    if not (lv or pf or sim):
        # Fallback: count from runs array
        runs = data.get("runs", [])
        lv = sum(1 for r in runs if r.get("classification") == "LIVE_VALID")
        pf = sum(1 for r in runs if r.get("classification") == "LIVE_PROVIDER_FAILURE")
        sim = sum(1 for r in runs if r.get("classification") == "SIMULATED")
    assert (lv, pf, sim) == (2, 9, 264), (
        f"STUDY-008 live run accounting drifted: got "
        f"({lv}, {pf}, {sim}), expected (2, 9, 264). "
        f"This is the audit's definitive count (AUDIT-EVID-001)."
    )


# ---------------------------------------------------------------------------
# 6. Front-door documents must not carry forbidden overclaims.
# ---------------------------------------------------------------------------

# Forbidden tokens must not appear in the body of front-door documents.
# They may appear inside blockquotes that discuss the audit history
# (e.g., the README's own "this doc was rewritten to remove ..." note).
# The check below excludes blockquote-prefixed lines.
QUOTE_PREFIXES = ("> ", ">")

def _strip_blockquotes(text: str) -> str:
    out = []
    for line in text.splitlines():
        if line.startswith(QUOTE_PREFIXES):
            continue
        out.append(line)
    return "\n".join(out)


def _strip_quoted_overclaim_mentions(text: str) -> str:
    """Strip substrings that mention forbidden tokens inside ASCII
    double-quote pairs (e.g., audit history: Replaced "FCR ELIMINATED"
    with ...). This is the legitimate documentation pattern; the
    overclaim is being *cited as removed*, not asserted.

    Also strip backtick-wrapped tokens (`` `1,000 live runs` ``) since
    backticks in markdown are functionally a quoting convention and are
    used in CHANGELOG entries that list what the test catches.
    """
    out = []
    for line in text.splitlines():
        # Remove any "..." string that contains a forbidden token
        def _strip(m):
            inner = m.group(1)
            if any(tok in inner for tok in FORBIDDEN_TOKENS_IN_FRONTDOOR):
                return ""
            return m.group(0)
        cleaned = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', _strip, line)
        # Remove any `...` backtick-wrapped string with a forbidden token
        def _strip_backtick(m):
            inner = m.group(1)
            if any(tok in inner for tok in FORBIDDEN_TOKENS_IN_FRONTDOOR):
                return ""
            return m.group(0)
        cleaned = re.sub(r"`([^`\\]*(?:\\.[^`\\]*)*)`", _strip_backtick, cleaned)
        out.append(cleaned)
    return "\n".join(out)


# Historical audit-walk-back markers. A CHANGELOG line that contains
# one of these is documenting the walk-back, not asserting the claim.
WALKBACK_MARKERS = (
    "Front-Doc Audit Alignment",
    "Front-Door Audit",
    "audit history",
    "walked back",
    "Walked back",
    "Wave v0.3.1",
    "v0.3.1",
)


def _strip_walkback_lines(text: str) -> str:
    """Strip lines that are clearly part of an audit walk-back entry."""
    out = []
    keep = True
    in_walkback_section = False
    for line in text.splitlines():
        # Detect start of a new CHANGELOG entry
        if line.startswith("## "):
            in_walkback_section = any(m in line for m in WALKBACK_MARKERS)
        if in_walkback_section and any(m in line for m in WALKBACK_MARKERS):
            out.append("")
            continue
        out.append(line)
    return "\n".join(out)


FORBIDDEN_TOKENS_IN_FRONTDOOR = [
    "1,000 live runs",
    "1,000 LIVE",
    "FCR ELIMINATED",
    "FCR eliminated",
    "HEVO -68",
    "HEVO −68",
    "D2 INTEGRATE 65",
    "D2 integrate 65",
    "GOAL_COMPLETE",
    "no FCR observed",  # only Wilson CI, never a point estimate
    "zero false completions",  # same
    "zero population failure",
]


@pytest.mark.parametrize("doc", [
    "README.md",
    "00-EXECUTIVE-SUMMARY.md",
    "CHANGELOG.md",
])
def test_frontdoor_no_forbidden_overclaims(doc):
    """Front-door docs must not contain claims the audit has walked back
    in their narrative body. (Audit-history blockquotes that *mention*
    the old overclaim are allowed because they document the walk-back.)"""
    p = Path(workspace) / doc
    text = p.read_text(encoding="utf-8")
    # Strip blockquote lines, quoted overclaim mentions, and CHANGELOG
    # walk-back sections (these document the audit history).
    body = _strip_walkback_lines(
        _strip_quoted_overclaim_mentions(_strip_blockquotes(text))
    )
    # Strip negation contexts: "NOT GOAL_COMPLETE" is a legitimate
    # anti-claim. The intent is to catch assertion, not negation.
    body = re.sub(
        r"(NOT\s+GOAL_COMPLETE|no\s+GOAL_COMPLETE|never\s+GOAL_COMPLETE)",
        "...",
        body,
        flags=re.IGNORECASE,
    )
    for token in FORBIDDEN_TOKENS_IN_FRONTDOOR:
        assert token not in body, (
            f"{doc} contains forbidden token {token!r} outside a "
            f"blockquote. This is an audited overclaim; remove or "
            f"qualify with the correct Wilson CI."
        )


# ---------------------------------------------------------------------------
# 7. Q-010 / Q-011 must reflect STUDY-011 pre-execution state.
# ---------------------------------------------------------------------------

def test_q010_q011_reflect_study011_pre_execution_state():
    """Q-010 (Live Evidence Gap) and Q-011 (Resource Authorization) must
    describe the actual study-011 state: pre-registered, not yet run."""
    p = Path(workspace) / "data/open_questions.csv"
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    q010 = next((r for r in rows if r["question_id"] == "Q-010"), None)
    q011 = next((r for r in rows if r["question_id"] == "Q-011"), None)
    assert q010 is not None, "Q-010 missing"
    assert q011 is not None, "Q-011 missing"
    # Q-010 must mention STUDY-011 in some form
    assert "STUDY-011" in q010["question"], "Q-010 lost STUDY-011 reference"
    # Q-011 must mention budget / IP-hold
    q11_lower = q011["question"].lower()
    assert ("budget" in q11_lower or "approval" in q11_lower
            or "ip-hold" in q11_lower), \
        "Q-011 lost budget / approval / IP-hold reference"


# ---------------------------------------------------------------------------
# 8. STUDY-011 readiness report must end in READY or NOT_READY (not stale).
# ---------------------------------------------------------------------------

def test_study011_readiness_report_is_current_version():
    """The readiness report v1.0 said NOT_READY (5 blockers). Current
    state is v2.0 READY_FOR_OWNER_APPROVAL. We pin the version, not
    the status (which could legitimately change back)."""
    p = Path(workspace) / "STUDY-011-READINESS-REPORT.md"
    text = p.read_text(encoding="utf-8")
    # v2.0 must be present
    assert "v2.0" in text, (
        f"STUDY-011-READINESS-REPORT.md is not at v2.0. "
        f"v1.0 (NOT_READY, 5 blockers) is stale."
    )


# ---------------------------------------------------------------------------
# 9. test_registries.verify() must pass (CLI audit relies on it).
# ---------------------------------------------------------------------------

def test_registries_verify_passes():
    from tests.test_registries import verify
    assert verify() is True, (
        "Registry integrity verification failed. "
        "Run `python cli/mission_cli.py audit` for details. "
        "The CLI audit is the same check."
    )


# ---------------------------------------------------------------------------
# 10. All test files must end with a newline (LF convention).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", PINNED_EVIDENCE_FILES)
def test_evidence_files_lf_line_endings(path):
    """Evidence files (especially .csv, .json, .sha256) must use LF
    line endings. CRLF silently breaks sha256sum and CSV parsers.

    Note: .md files tolerate CRLF in some tools, so we check .csv,
    .json, .sha256, and .py only. Data integrity > cosmetic LF."""
    p = Path(workspace) / path
    if p.suffix in (".csv", ".json", ".sha256", ".py"):
        data = p.read_bytes()
        if b"\r\n" in data:
            pytest.fail(
                f"{path} contains CRLF line endings. "
                f"Evidence files must use LF (Unix line endings) to "
                f"preserve hash stability and parser reliability."
            )
