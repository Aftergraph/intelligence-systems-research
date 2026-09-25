"""Offline G15 technical preflight.

Never authorizes confirmatory execution. G15-9 remains a separate owner gate.
"""
from __future__ import annotations

import json
from pathlib import Path

from .analyze import analyze
from .dry_run import build_matrix
from .freeze_manifest import build_freeze_manifest
from .owner_gate import OwnerGateError, assert_owner_approved
from .power_analysis import draft_plan
from .validate_envelope import load_schema

ROOT = Path(__file__).resolve().parents[2]


def run_preflight() -> dict:
    load_schema()

    dry_rows = build_matrix()
    analysis = analyze(dry_rows, allow_dry_run=True)
    freeze = build_freeze_manifest(status="DRAFT")
    power = draft_plan()

    owner = json.loads((ROOT / "data" / "study015_owner_gate.json").read_text(encoding="utf-8"))
    owner_pending = False
    try:
        assert_owner_approved(owner)
    except OwnerGateError:
        owner_pending = True

    checks = {
        "G15-0_methodology_artifact": (ROOT / "docs/studies/STUDY-015-G15-0-METHODOLOGY-REVIEW.md").exists(),
        "G15-1_schema_loaded": True,
        "G15-2_workload_manifest": (ROOT / "data/study015_workload_failure_manifest.json").exists(),
        "G15-3_freeze_builder": freeze["status"] == "DRAFT" and len(freeze["implementation_fingerprint"]) == 64,
        "G15-4_condition_isolation_exercised": len(dry_rows) == 22,
        "G15-5_power_plan": power["status"] == "DRAFT_NOT_FROZEN",
        "G15-6_analyzer": analysis["n"] == len(dry_rows),
        "G15-7_dry_run_never_live": all(not row["is_live"] for row in dry_rows),
        "G15-8_admissibility_code": (ROOT / "experiments/study015/admissibility.py").exists(),
        "G15-9_owner_gate_pending": owner_pending,
    }
    technical = all(value for key, value in checks.items() if key != "G15-9_owner_gate_pending")
    return {
        "status": "TECHNICAL_BUILD_PASS" if technical else "TECHNICAL_BUILD_FAIL",
        "confirmatory_execution_authorized": False,
        "checks": checks,
        "dry_run_records": len(dry_rows),
        "protocol_sha256_draft": freeze["protocol_sha256"],
        "implementation_fingerprint_draft": freeze["implementation_fingerprint"],
    }


def main() -> int:
    result = run_preflight()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "TECHNICAL_BUILD_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
