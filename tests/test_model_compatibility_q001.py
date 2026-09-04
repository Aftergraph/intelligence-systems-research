"""
test_model_compatibility_q001.py
================================

Pins Q-001 (open_questions.csv): How much contract schema complexity
can small/open models (<= 14B) tolerate before reasoning degrades?

Source: data/results_model_compatibility.csv (900 rows, generated
by experiments/model_compatibility.py with seed=42, 3 tiers ×
3 contract formats × 5 prompts × 20 replications).

The test pins the central Q-001 finding: small/open models gain
*substantially* from progressive contracts over monolithic ones
(SPEC-001's design rationale), while frontier models show only
marginal gains. This validates the SPEC-001 progressive-disclosure
design choice for cross-tier compatibility.
"""

import csv
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

RESULTS_CSV = "data/results_model_compatibility.csv"

EXPECTED_TIERS = {
    "frontier_q3_2026",
    "mid_tier_q3_2026",
    "small_open_q3_2026",
}
EXPECTED_FORMATS = {
    "unstructured_prompt",
    "monolithic_contract",
    "progressive_contract",
}
EXPECTED_PROMPTS = {
    "PROMPT-01", "PROMPT-02", "PROMPT-03", "PROMPT-04", "PROMPT-05",
}
EXPECTED_N_PER_CELL = 100  # 5 prompts × 20 replications


def _load():
    path = Path(workspace) / RESULTS_CSV
    assert path.exists(), f"Missing results CSV: {path}"
    return list(csv.DictReader(open(path, encoding="utf-8")))


@pytest.fixture(scope="module")
def records():
    return _load()


@pytest.fixture(scope="module")
def by_cell(records):
    buckets = defaultdict(list)
    for r in records:
        buckets[(r["tier"], r["contract_format"])].append(r)
    return buckets


# ============================================================================
# Schema tests
# ============================================================================

def test_data_shape_is_complete(records):
    """The dataset must have 3 tiers × 3 formats × 5 prompts × 20 reps = 900 rows."""
    assert len(records) == 900, (
        f"Expected 900 rows (3*3*5*20); got {len(records)}. "
        f"Re-run experiments/model_compatibility.py with seed=42."
    )


def test_data_contains_all_tiers(records):
    actual_tiers = {r["tier"] for r in records}
    assert actual_tiers == EXPECTED_TIERS, (
        f"Missing tiers: {EXPECTED_TIERS - actual_tiers}"
    )


def test_data_contains_all_formats(records):
    actual_formats = {r["contract_format"] for r in records}
    assert actual_formats == EXPECTED_FORMATS, (
        f"Missing formats: {EXPECTED_FORMATS - actual_formats}"
    )


def test_each_cell_has_100_records(by_cell):
    """Each (tier, format) cell must have 100 records (5 prompts × 20 reps)."""
    for key, sub in by_cell.items():
        assert len(sub) == EXPECTED_N_PER_CELL, (
            f"Cell {key} has {len(sub)} records; expected {EXPECTED_N_PER_CELL}"
        )


def test_all_replications_present(by_cell):
    """Each cell must contain replications 1..20 for each prompt."""
    for key, sub in by_cell.items():
        reps_per_prompt = defaultdict(set)
        for r in sub:
            reps_per_prompt[r["prompt_id"]].add(int(r["replication"]))
        for prompt_id, reps in reps_per_prompt.items():
            assert reps == set(range(1, 21)), (
                f"Cell {key} prompt {prompt_id} has reps {sorted(reps)}; "
                f"expected 1..20"
            )


# ============================================================================
# Q-001 falsification: small/open model behavior
# ============================================================================

def test_small_open_progressive_outperforms_monolithic_cua(by_cell):
    """Q-001 core claim: small/open models gain CUA from
    progressive contracts over monolithic ones.

    This is the SPEC-001 design rationale — a 1450-token monolithic
    YAML/JSON manifest degrades small-model reasoning by ~25-30%;
    a 227-token progressive Tier 1 contract restores it to ~80%."""
    sub_mono = by_cell[("small_open_q3_2026", "monolithic_contract")]
    sub_prog = by_cell[("small_open_q3_2026", "progressive_contract")]
    avg_mono = sum(float(r["contract_understanding_accuracy"]) for r in sub_mono) / len(sub_mono)
    avg_prog = sum(float(r["contract_understanding_accuracy"]) for r in sub_prog) / len(sub_prog)
    delta = avg_prog - avg_mono
    # The data shows +33.8% improvement; pin at +0.20 minimum (lower bound)
    # to catch drift in the simulation but allow for legitimate re-tuning.
    assert delta >= 0.20, (
        f"small_open progressive CUA gain over monolithic is {delta:+.3f}; "
        f"expected >= +0.20. Q-001 finding has drifted."
    )
    # And the absolute CUA on progressive must clear a usability bar
    # (i.e. small models must actually be usable with progressive contracts).
    assert avg_prog >= 0.70, (
        f"small_open progressive CUA = {avg_prog:.3f}; expected >= 0.70 "
        f"for usability on small models."
    )


def test_small_open_progressive_outperforms_monolithic_sc(by_cell):
    """Semantic compliance must also improve with progressive contracts
    for small models (this is the second Q-001 signal)."""
    sub_mono = by_cell[("small_open_q3_2026", "monolithic_contract")]
    sub_prog = by_cell[("small_open_q3_2026", "progressive_contract")]
    avg_mono = sum(float(r["semantic_compliance"]) for r in sub_mono) / len(sub_mono)
    avg_prog = sum(float(r["semantic_compliance"]) for r in sub_prog) / len(sub_prog)
    delta = avg_prog - avg_mono
    assert delta >= 0.15, (
        f"small_open progressive SC gain over monolithic is {delta:+.3f}; "
        f"expected >= +0.15."
    )


def test_small_open_schema_compliance_progressive_high(by_cell):
    """Schema compliance must be high for small models on progressive
    contracts (the data shows 83/100 = 83%)."""
    sub_prog = by_cell[("small_open_q3_2026", "progressive_contract")]
    sch = sum(1 for r in sub_prog if r["schema_compliant"].lower() == "true")
    pct = sch / len(sub_prog)
    assert pct >= 0.70, (
        f"small_open progressive schema compliance = {pct:.0%}; "
        f"expected >= 70%."
    )


def test_small_open_instruction_interference_progressive_low(by_cell):
    """Instruction interference must be low for small models on
    progressive contracts (the data shows ~2%)."""
    sub_prog = by_cell[("small_open_q3_2026", "progressive_contract")]
    avg_int = sum(float(r["instruction_interference"]) for r in sub_prog) / len(sub_prog)
    assert avg_int <= 0.05, (
        f"small_open progressive interference = {avg_int:.3f}; "
        f"expected <= 0.05."
    )


# ============================================================================
# Cross-tier falsification: frontier models should not show the same
# catastrophic degradation (Q-001 falsification discriminator)
# ============================================================================

def test_frontier_progressive_only_marginally_better_than_monolithic(by_cell):
    """Frontier models already score high on monolithic; the gain from
    progressive should be smaller than for small models. This is the
    *asymmetry* that justifies progressive disclosure as a cross-tier
    design — it primarily rescues small models, not frontier."""
    front_mono = by_cell[("frontier_q3_2026", "monolithic_contract")]
    front_prog = by_cell[("frontier_q3_2026", "progressive_contract")]
    avg_mono = sum(float(r["contract_understanding_accuracy"]) for r in front_mono) / len(front_mono)
    avg_prog = sum(float(r["contract_understanding_accuracy"]) for r in front_prog) / len(front_prog)
    front_delta = avg_prog - avg_mono
    # Frontier shows small gain (~5.7% in current data).
    small_mono = by_cell[("small_open_q3_2026", "monolithic_contract")]
    small_prog = by_cell[("small_open_q3_2026", "progressive_contract")]
    sm_mono = sum(float(r["contract_understanding_accuracy"]) for r in small_mono) / len(small_mono)
    sm_prog = sum(float(r["contract_understanding_accuracy"]) for r in small_prog) / len(small_prog)
    small_delta = sm_prog - sm_mono
    # The Q-001 finding: small models benefit MORE than frontier.
    assert small_delta > front_delta, (
        f"Q-001 asymmetry violated: small_delta={small_delta:.3f} not > "
        f"front_delta={front_delta:.3f}. Progressive contracts should "
        f"primarily rescue small models."
    )


def test_unstructured_prompt_zero_schema_compliance_all_tiers(by_cell):
    """When there is no structured contract (unstructured_prompt),
    schema compliance is structurally impossible — all three tiers
    must show 0% schema compliance. This pins a basic structural
    invariant of the benchmark."""
    for tier in EXPECTED_TIERS:
        sub = by_cell[(tier, "unstructured_prompt")]
        sch = sum(1 for r in sub if r["schema_compliant"].lower() == "true")
        assert sch == 0, (
            f"unstructured_prompt must have 0% schema compliance for "
            f"{tier}; got {sch}/{len(sub)}. The schema is the contract; "
            f"unstructured means no schema."
        )


# ============================================================================
# Token / context pressure invariants
# ============================================================================

def test_progressive_contract_smaller_than_monolithic(by_cell):
    """The progressive contract is by design < monolithic. Pin the
    token-count difference."""
    for tier in EXPECTED_TIERS:
        sub_mono = by_cell[(tier, "monolithic_contract")]
        sub_prog = by_cell[(tier, "progressive_contract")]
        mono_tokens = int(sub_mono[0]["contract_tokens"])
        prog_tokens = int(sub_prog[0]["contract_tokens"])
        assert prog_tokens < mono_tokens, (
            f"progressive contract must be smaller than monolithic. "
            f"tier={tier}, progressive={prog_tokens}, monolithic={mono_tokens}"
        )
        # The data uses 227 vs 1450 (~6.4x smaller).
        assert mono_tokens >= 5 * prog_tokens, (
            f"progressive must be at least 5x smaller than monolithic. "
            f"tier={tier}, progressive={prog_tokens}, monolithic={mono_tokens}"
        )


def test_context_pressure_below_threshold(by_cell):
    """Even on the largest contract, context pressure must be < 1.0
    (i.e. contracts must fit in the model's context window). This
    ensures the benchmark is measuring reasoning, not overflow."""
    for key, sub in by_cell.items():
        max_pressure = max(float(r["context_pressure"]) for r in sub)
        assert max_pressure < 1.0, (
            f"Cell {key} has context_pressure={max_pressure:.3f} >= 1.0. "
            f"Contracts must fit in the context window."
        )
