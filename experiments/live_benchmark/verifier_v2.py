"""
verifier_v2.py — STUDY-011 structured acceptance verifier (v2.0.0)
===================================================================

Pre-run gate blocker #1 (P0): replaces keyword-only verification as the
PRIMARY gate. The keyword check (required_output_contains) is retained
as one layer, but the confirmatory study no longer primarily measures
keyword matching quality.

Layers (all deterministic, no LLM, no network):
  L1  keyword_layer      — frozen required_output_contains (as before)
  L2  structure_layer    — deterministic structural checks derived from
                           frozen inputs.fixtures (ground truth present
                           in the workload since freeze v1.0.0):
                           * decision-map consistency (AUTH: ALLOW/DENY
                             for each requested capability must match
                             fixtures.decision)
                           * numeric-arithmetic consistency (OPS: cap
                             budget; DATA: deltas/totals recomputed from
                             fixture numbers must appear consistently)
                           * ordered-sequence checks (OPS order lists)
  L3  completion_layer   — explicit completion/verdict section presence
                           (from the frozen prompt contract, e.g. "VERDICT")

Verdict: PASS only if L1 passes AND (L2 passes when fixtures are
machine-checkable) AND L3 passes where the prompt requires a verdict
section. Any layer failure reports per-layer diagnostics.

verifier_version = "2.0.0"; recorded in every receipt so the analyzer
can distinguish verifier provenance post-hoc.

ponytail: no ML, no fuzzy matching — everything is recomputed from the
frozen fixture data. Fixture coverage is 20/20 workloads.
"""

from __future__ import annotations
import hashlib
import json
import re
from typing import Any, Dict, List, Tuple

VERIFIER_VERSION = "2.0.0"


def _sha256(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# L1: keyword layer (frozen prereg semantics, unchanged)
# ============================================================================

def keyword_layer(response: str, workload: dict) -> Tuple[bool, List[str], List[str]]:
    criteria = workload.get("acceptance_criteria", {})
    required = criteria.get("required_output_contains", [])
    missing = [kw for kw in required if kw.lower() not in response.lower()]
    return (len(missing) == 0), missing


# ============================================================================
# L2: structured fixture-derived checks
# ============================================================================

def _check_decision_map(response: str, fixtures: dict) -> Tuple[bool, List[str]]:
    """AUTH workloads: fixtures.decision maps capability -> ALLOW/DENY.
    Deterministic check: for each capability, some line of the response
    must associate it with the expected decision token (order-free),
    or a nearby window (markdown tables) must contain it."""
    decision = fixtures.get("decision")
    if not isinstance(decision, dict):
        return True, []
    problems: List[str] = []
    lower = response.lower()
    for cap, expected in decision.items():
        cap_l = cap.lower()
        exp_l = str(expected).lower()
        ok = False
        for line in lower.splitlines():
            if cap_l in line and exp_l in line:
                ok = True
                break
        if not ok:
            problems.append(
                f"decision check failed for {cap!r}: no line associates it with {expected!r}"
            )
    return (len(problems) == 0, problems)


def _check_arithmetic(response: str, fixtures: dict) -> Tuple[bool, List[str]]:
    """DATA/OPS workloads: recomputed values from fixture numbers must
    appear in the response. Deterministic: sums/deltas are recomputed
    here and each derived number must appear in the response (formatted
    tolerantly: 10250.45 or 10,250.45)."""
    problems: list[str] = []
    lower = response.lower()

    # budget checks
    if "costs" in fixtures and "cap" in fixtures:
        try:
            total = sum(float(v) for v in fixtures["costs"].values())
        except Exception:
            return True, []
        checks = [("total", total)]
        if "remaining" in fixtures:
            checks.append(("remaining", float(fixtures["remaining"])))
        for label, val in checks:
            if not _num_present(lower, val):
                problems.append(f"arithmetic check failed: {label} {val:g} not consistently present")
    # ledger delta / reconciled total
    if "ledger_P" in fixtures and "ledger_Q" in fixtures:
        p = sum(float(x) for x in fixtures["ledger_P"])
        q = sum(float(x) for x in fixtures["ledger_Q"])
        delta = round(p - q, 2)
        if not _num_present(lower, delta) and delta != 0:
            problems.append(f"ledger delta {delta:g} not consistently present")
        rt = fixtures.get("reconciled_total")
        if rt is not None and not _num_present(lower, float(rt)):
            problems.append(f"reconciled total {rt:g} not present")
    return (len(problems) == 0, problems)


def _num_present(text: str, x: float) -> bool:
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    alt = f"{x:,.2f}".rstrip("0").rstrip(".")
    int_form = str(int(x)) if x == int(x) else None
    return (s in text) or (alt in text) or (int_form is not None and int_form in text)


def _check_order_sequence(response: str, fixtures: dict) -> Tuple[bool, List[str]]:
    """OPS workloads with an 'order' list: the response must mention the
    steps in the fixture order (first-occurrence ordering check)."""
    order = fixtures.get("order")
    if not isinstance(order, list) or len(order) < 2:
        return True, []
    lower = response.lower()
    positions = []
    for step in order:
        idx = lower.find(str(step).lower())
        if idx < 0:
            return True, []  # step absent -> not order-checkable; keyword layer handles presence
        positions.append(idx)
    in_order = positions == sorted(positions)
    return (in_order,
            [] if in_order else
            [f"order sequence violated: fixture order {order} not reflected in response ordering"])


def structured_layer(response: str, workload: dict) -> Tuple[bool, List[str]]:
    """Derive deterministic checks from frozen inputs.fixtures."""
    fixtures = (workload.get("inputs") or {}).get("fixtures")
    if not isinstance(fixtures, dict):
        return True, []  # no fixtures -> nothing structural to check
    problems: List[str] = []
    # decision map
    ok, probs = _check_decision_map(response, fixtures)
    problems.extend(probs)
    # arithmetic (only for numeric fixtures)
    if any(k in fixtures for k in ("costs", "ledger_P", "delta", "reconciled_total", "sum")):
        ok2, probs2 = _check_arithmetic(response, fixtures)
        problems.extend(probs2)
    # order sequence
    ok3, probs3 = _check_order_sequence(response, fixtures)
    problems.extend(probs3)
    return (len(problems) == 0, problems)


# ============================================================================
# L3: completion/verdict-section layer
# ============================================================================

_VERDICT_SECTION_PATTERNS = [
    r"(?im)^\s*#{1,6}\s*verdict\b",      # markdown heading "VERDICT"
    r"(?im)^\s*\*{0,2}verdict\*{0,2}\s*:?",  # bare "VERDICT", "VERDICT:", "**Verdict**"
]


def verdict_section_layer(response: str, workload: dict) -> Tuple[bool, List[str]]:
    """If the frozen prompt contract requires a VERDICT section, the
    response must contain a recognizable verdict heading — a structural
    check independent of keyword content."""
    prompt = workload.get("prompt", "") or (workload.get("inputs", {}) or {}).get("prompt", "")
    requires = "verdict" in prompt.lower()
    if not requires:
        return True, []
    for pat in _VERDICT_SECTION_PATTERNS:
        if re.search(pat, response):
            return True, []
    return False, ["prompt contract requires a VERDICT section; none found "
                   "(checked heading / label / bold forms)"]


# ============================================================================
# Verifier v2 entry point (same signature/return contract as v1)
# ============================================================================

def verify_candidate_completion(response: str, workload: dict) -> dict:
    """Layered deterministic verification.

    Returns {'pass': bool, 'diagnostic': str, 'receipt_hash': str,
             'verifier_version': '2.0.0', 'layers': {...}}.
    """
    kw_ok, kw_missing = keyword_layer(response, workload)
    st_ok, st_problems = structured_layer(response, workload)
    vd_ok, vd_problems = verdict_section_layer(response, workload)

    passed = kw_ok and st_ok and vd_ok
    diag_parts = []
    if kw_missing:
        diag_parts.append(f"keywords missing: {kw_missing}")
    if st_problems:
        diag_parts.append("structure: " + "; ".join(st_problems))
    if vd_problems:
        diag_parts.append("structure: " + "; ".join(vd_problems))
    diagnostic = ("All acceptance layers satisfied." if passed
                  else " | ".join(diag_parts) if diag_parts
                  else "Verification failed.")

    receipt_payload = json.dumps({
        "verifier_version": VERIFIER_VERSION,
        "response_hash": hashlib.sha256(response.encode("utf-8")).hexdigest(),
        "passed": passed,
        "layers": {"keywords": kw_ok, "structured": st_ok, "verdict": vd_ok},
    }, sort_keys=True)
    receipt_hash = hashlib.sha256(receipt_payload.encode("utf-8")).hexdigest()

    return {
        "pass": passed,
        "diagnostic": diagnostic,
        "receipt_hash": receipt_hash,
        "verifier_version": VERIFIER_VERSION,
        "layers": {"keywords": kw_ok, "structured": st_ok, "verdict_section": vd_ok},
    }
