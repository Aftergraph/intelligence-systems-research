"""Deterministic, offline-only STUDY-015 dry-run harness.

This does not call providers and can never emit LIVE_VALID records.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .condition_isolation import assert_mechanism_isolation, expected_mechanisms
from .source_fingerprint import canonical_fingerprint, load_heads
from .validate_envelope import validate_envelope

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "data" / "study015_fixtures" / "valid_envelope.json"


def _base() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def build_dry_run(condition: str, *, workload_id: str, replicate_id: int) -> dict[str, Any]:
    row = copy.deepcopy(_base())
    heads = load_heads()
    row.update(
        run_id=f"dry-{condition.lower()}-{workload_id.lower()}-r{replicate_id}",
        mission_id=f"dry-mission-{workload_id.lower()}",
        condition=condition,
        execution_class="DRY_RUN",
        is_live=False,
        provider="offline-deterministic-harness",
        model="no-model",
        workload_id=workload_id,
        replicate_id=replicate_id,
        source_heads=heads,
        implementation_fingerprint=canonical_fingerprint(heads),
    )

    mechanisms = set(expected_mechanisms(condition))
    assert_mechanism_isolation(condition=condition, observed_enabled=mechanisms)

    # Dry-run outcome data exists only to exercise the measurement pipeline.
    # It is never admissible as confirmatory evidence.
    stage = 10 if condition == "FULL" else int(condition[1:]) if condition.startswith("S") else 0
    verified = stage >= 3
    row["outcome"].update(
        declared_complete=True,
        verified_success=verified,
        false_completion=not verified,
        unauthorized_action=False,
        abstained=False,
        recovery_attempted=stage >= 5,
        recovery_success=True if stage >= 5 else None,
        human_interventions=0,
        final_state="VERIFIED" if verified else "DECLARED_ONLY",
    )
    row["verification"].update(
        independent=verified,
        verifier_id="dry-independent-verifier" if verified else None,
        verification_subject=f"dry-subject:{workload_id}" if verified else None,
        evidence_root=f"dry-evidence:{condition}:{workload_id}" if verified else None,
        verdict="PASS" if verified else "NOT_RUN",
        evidence_invalidations=0,
    )
    row["performance"].update(
        latency_ms=1000 + stage * 25,
        time_to_verified_ms=(1100 + stage * 25) if verified else None,
        total_cost_usd=0.0,
        tokens_total=1000 + stage * 10,
        control_plane_tokens=stage * 5,
        compute_ms=900 + stage * 20,
        provider_cost_usd=0.0,
        verification_cost_usd=0.0,
        control_plane_cost_usd=0.0,
    )
    return validate_envelope(row)


def build_matrix() -> list[dict[str, Any]]:
    conditions = [f"S{i}" for i in range(10)] + ["FULL"]
    workloads = ["S15-SWE-01", "S15-AUTH-01"]
    return [
        build_dry_run(condition, workload_id=workload, replicate_id=0)
        for condition in conditions
        for workload in workloads
    ]


def main() -> int:
    rows = build_matrix()
    print(json.dumps({"status": "PASS", "records": len(rows), "live_records": sum(r["is_live"] for r in rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
