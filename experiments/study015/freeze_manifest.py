"""Build a reproducible STUDY-015 protocol freeze manifest.

The builder can emit DRAFT or FROZEN metadata, but confirmatory admissibility
still requires the separate explicit owner gate.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .source_fingerprint import canonical_fingerprint, load_heads

ROOT = Path(__file__).resolve().parents[2]

PROTOCOL_ARTIFACTS = (
    "STUDY-015-PREREGISTRATION.md",
    "data/study015_performance_envelope.schema.json",
    "data/study015_condition_manifest.json",
    "data/study015_workload_failure_manifest.json",
    "data/study015_power_plan.draft.json",
    "experiments/study015/analyze.py",
    "experiments/study015/admissibility.py",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_freeze_manifest(*, status: str = "DRAFT") -> dict[str, Any]:
    if status not in {"DRAFT", "FROZEN"}:
        raise ValueError("status must be DRAFT or FROZEN")
    heads = load_heads()
    artifacts = {path: sha256_file(ROOT / path) for path in PROTOCOL_ARTIFACTS}
    protocol_payload = "\n".join(f"{path}={artifacts[path]}" for path in sorted(artifacts)) + "\n"
    protocol_sha = hashlib.sha256(protocol_payload.encode("utf-8")).hexdigest()
    return {
        "schema": "study015.freeze-manifest/0.1.0",
        "study_id": "STUDY-015",
        "status": status,
        "protocol_sha256": protocol_sha,
        "implementation_fingerprint": canonical_fingerprint(heads),
        "source_heads": heads,
        "artifacts": artifacts,
        "owner_gate_required": True,
    }


def write_manifest(path: Path, *, status: str = "DRAFT") -> None:
    path.write_text(
        json.dumps(build_freeze_manifest(status=status), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
