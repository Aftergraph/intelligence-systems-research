"""Deterministic calculator/validator for research metrics receipts v0.1."""
from __future__ import annotations
import json
from pathlib import Path

def _ratio(n, d):
    return None if d == 0 else n / d

def validate(receipt: dict) -> None:
    c = receipt["counters"]
    checks = [
        ("deterministically_verified_claims", "verifiable_claims"),
        ("judge_only_verified_claims", "verified_claims"),
        ("independently_verified_claims", "verified_claims"),
        ("replication_successes", "replication_attempts"),
        ("reproducible_counterexamples", "falsification_attempts"),
        ("covered_adversarial_classes", "applicable_adversarial_classes"),
    ]
    for n, d in checks:
        if c[n] > c[d]:
            raise ValueError(f"{n} cannot exceed {d}")
    if not receipt["population"].strip() or not receipt["run_set_ref"].strip():
        raise ValueError("population and run_set_ref are required")
    if not receipt["provenance"]["source_commit"].strip():
        raise ValueError("source_commit is required")

def calculate(receipt: dict) -> dict:
    validate(receipt)
    c, r = receipt["counters"], receipt["resources"]
    progress = c["research_progress_events"]
    return {
        "dvcr": _ratio(c["deterministically_verified_claims"], c["verifiable_claims"]),
        "jcr": _ratio(c["judge_only_verified_claims"], c["verified_claims"]),
        "ivcr": _ratio(c["independently_verified_claims"], c["verified_claims"]),
        "replication_success_rate": _ratio(c["replication_successes"], c["replication_attempts"]),
        "falsification_yield": _ratio(c["reproducible_counterexamples"], c["falsification_attempts"]),
        "adversarial_coverage": _ratio(c["covered_adversarial_classes"], c["applicable_adversarial_classes"]),
        "verified_progress_per_cost_usd": None if r["cost_usd"] in (None, 0) else progress / r["cost_usd"],
        "verified_progress_per_1k_tokens": None if r["tokens"] in (None, 0) else progress / (r["tokens"] / 1000),
        "verified_progress_per_hour": None if r["wall_clock_seconds"] in (None, 0) else progress / (r["wall_clock_seconds"] / 3600),
    }

def load_and_calculate(path: str | Path) -> dict:
    return calculate(json.loads(Path(path).read_text(encoding="utf-8")))
