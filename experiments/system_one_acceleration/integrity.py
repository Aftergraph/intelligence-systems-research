"""Content-addressed integrity manifests for JAR-EXP-0014 authorization gates."""

from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable


CALIBRATION_INTEGRITY_PATHS = (
    "experiments/system_one_acceleration/adapter.py",
    "experiments/system_one_acceleration/calibration.py",
    "experiments/system_one_acceleration/calibration_preflight.py",
    "experiments/system_one_acceleration/calibration_receipt.py",
    "experiments/system_one_acceleration/calibration_runner.py",
    "experiments/system_one_acceleration/client.py",
    "experiments/system_one_acceleration/corpus.py",
    "experiments/system_one_acceleration/guarded_calibration.py",
    "experiments/system_one_acceleration/integrity.py",
    "experiments/system_one_acceleration/protocol.py",
    "data/jar_exp_0014_calibration_protocol_v01.json",
    "data/jar_exp_0014_question_contracts_v01.json",
    "requirements-typesafe.txt",
    "schemas/system-one-calibration-approval-receipt.v0.1.json",
    "schemas/system-one-calibration-receipt.v0.1.json",
)


def content_manifest_sha256(root: Path, paths: Iterable[str]) -> str:
    root = Path(root).resolve()
    entries = []
    for rel in sorted(paths):
        path = (root / rel).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"manifest path escapes repository root: {rel}") from exc
        data = path.read_bytes()
        entries.append({"path": rel, "sha256": sha256(data).hexdigest()})

    payload = json.dumps(
        entries, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def calibration_manifest_sha256(root: Path) -> str:
    return content_manifest_sha256(root, CALIBRATION_INTEGRITY_PATHS)
