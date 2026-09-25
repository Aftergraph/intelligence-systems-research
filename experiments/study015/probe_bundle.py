"""Validate and compose imported STUDY-015 component probe artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .probe_fabric import (
    ProbeFabricError,
    compose,
    load_json,
    validate_receipt,
    TARGETS_PATH,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDEX = ROOT / "data" / "study015_probe_receipts" / "current" / "index.json"


class ProbeBundleError(ProbeFabricError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_bundle(index_path: Path = DEFAULT_INDEX) -> dict[str, Any]:
    index = load_json(index_path)
    if index.get("schema") != "study015.probe-bundle-index/1.0":
        raise ProbeBundleError("invalid probe bundle index schema")
    if index.get("study_id") != "STUDY-015":
        raise ProbeBundleError("invalid study_id")

    targets_doc = load_json(TARGETS_PATH)
    targets = {row["component"]: row for row in targets_doc["targets"]}
    entries = index.get("receipts")
    if not isinstance(entries, list):
        raise ProbeBundleError("bundle index receipts must be a list")
    if {entry.get("component") for entry in entries} != set(targets):
        raise ProbeBundleError("bundle must contain exactly the target component set")

    receipts: list[dict[str, Any]] = []
    provenance: dict[str, Any] = {}
    base = index_path.parent.resolve()

    for entry in entries:
        component = entry["component"]
        target = targets[component]
        if entry.get("repository") != target["repository"]:
            raise ProbeBundleError(f"repository mismatch for {component}")
        if entry.get("source_head") != target["expected_head"]:
            raise ProbeBundleError(f"index source-head mismatch for {component}")

        digest = str(entry.get("artifact_digest") or "")
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise ProbeBundleError(f"invalid artifact digest for {component}")
        if not isinstance(entry.get("workflow_run_id"), int) or entry["workflow_run_id"] <= 0:
            raise ProbeBundleError(f"invalid workflow_run_id for {component}")
        if not isinstance(entry.get("artifact_id"), int) or entry["artifact_id"] <= 0:
            raise ProbeBundleError(f"invalid artifact_id for {component}")

        receipt_path = (base / entry["receipt_path"]).resolve()
        if receipt_path.parent != base:
            raise ProbeBundleError(f"receipt path escapes bundle directory: {component}")
        if not receipt_path.is_file():
            raise ProbeBundleError(f"missing receipt file for {component}")

        actual_sha = sha256_file(receipt_path)
        if actual_sha != entry.get("receipt_sha256"):
            raise ProbeBundleError(f"receipt SHA mismatch for {component}")

        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        validate_receipt(receipt, target=target)
        receipts.append(receipt)
        provenance[component] = {
            "repository": entry["repository"],
            "source_head": entry["source_head"],
            "workflow_run_id": entry["workflow_run_id"],
            "artifact_id": entry["artifact_id"],
            "artifact_name": entry.get("artifact_name"),
            "artifact_digest": digest,
            "receipt_sha256": actual_sha,
        }

    result = compose(receipts)
    result["artifact_provenance"] = provenance
    result["bundle_index_sha256"] = sha256_file(index_path)
    return result


def main() -> int:
    result = validate_bundle()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
