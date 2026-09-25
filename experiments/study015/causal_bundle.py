"""Validate the receipt-bound STUDY-015 causal composition layer."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .probe_bundle import validate_bundle

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDEX = ROOT / "data" / "study015_causal_receipts" / "current" / "index.json"


class CausalBundleError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_causal_root(
    *,
    component_probe_root_sha256: str,
    steward_source_head: str,
    steward_receipt_sha256: str,
    steward_artifact_digest: str,
) -> str:
    payload = "\n".join([
        f"component_probe_root_sha256={component_probe_root_sha256}",
        f"steward_source_head={steward_source_head}",
        f"steward_receipt_sha256={steward_receipt_sha256}",
        f"steward_artifact_digest={steward_artifact_digest}",
    ]) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_causal_bundle(index_path: Path = DEFAULT_INDEX) -> dict[str, Any]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if index.get("schema") != "study015.causal-bundle-index/1.0":
        raise CausalBundleError("invalid causal bundle index schema")
    if index.get("study_id") != "STUDY-015":
        raise CausalBundleError("invalid study_id")

    component = validate_bundle()
    component_root = component["probe_root_sha256"]
    if index.get("component_probe_root_sha256") != component_root:
        raise CausalBundleError("causal bundle component root mismatch")

    steward = index.get("steward")
    if not isinstance(steward, dict):
        raise CausalBundleError("missing steward provenance")

    receipt_path = (index_path.parent.resolve() / steward["receipt_path"]).resolve()
    if receipt_path.parent != index_path.parent.resolve():
        raise CausalBundleError("causal receipt path escapes bundle directory")
    if not receipt_path.is_file():
        raise CausalBundleError("missing causal receipt")

    receipt_sha = sha256_file(receipt_path)
    if receipt_sha != steward.get("receipt_sha256"):
        raise CausalBundleError("causal receipt SHA mismatch")

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "study015.causal-composition/1.0":
        raise CausalBundleError("invalid causal receipt schema")
    if receipt.get("component") != "steward-composition":
        raise CausalBundleError("unexpected causal component")
    if receipt.get("source_head") != steward.get("source_head"):
        raise CausalBundleError("STEWARD source-head mismatch")
    if receipt.get("component_probe_root_sha256") != component_root:
        raise CausalBundleError("causal receipt is bound to another component root")
    if receipt.get("component_heads") != component.get("source_heads"):
        raise CausalBundleError("causal receipt component-head map mismatch")
    if receipt.get("network_used") is not False:
        raise CausalBundleError("local causal probe unexpectedly used network")
    if not receipt.get("seams") or not all(receipt["seams"].values()):
        raise CausalBundleError("not all causal seams are proven")
    if not receipt.get("hostile") or not all(receipt["hostile"].values()):
        raise CausalBundleError("not all hostile seam checks are proven")

    identity = receipt.get("identity") or {}
    exact_subject = identity.get("exact_subject")
    head = identity.get("verification_head_sha")
    if not isinstance(exact_subject, str) or not isinstance(head, str):
        raise CausalBundleError("missing exact verification identity")
    if not exact_subject.endswith("@" + head):
        raise CausalBundleError("exact subject and verification head diverge")

    digest = str(steward.get("artifact_digest") or "")
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise CausalBundleError("invalid causal artifact digest")
    for key in ("workflow_run_id", "artifact_id"):
        if not isinstance(steward.get(key), int) or steward[key] <= 0:
            raise CausalBundleError(f"invalid {key}")

    root = compute_causal_root(
        component_probe_root_sha256=component_root,
        steward_source_head=steward["source_head"],
        steward_receipt_sha256=receipt_sha,
        steward_artifact_digest=digest,
    )
    if root != index.get("causal_root_sha256"):
        raise CausalBundleError("causal root mismatch")

    return {
        "schema": "study015.causal-bundle/1.0",
        "study_id": "STUDY-015",
        "component_probe_root_sha256": component_root,
        "causal_root_sha256": root,
        "steward_source_head": steward["source_head"],
        "identity": identity,
        "seams": receipt["seams"],
        "hostile": receipt["hostile"],
        "artifact_provenance": steward,
        "evidence_class": "LOCAL_EXACT_HEAD_COMPOSITION_CONTRACT",
        "live_performance_claim": False,
    }


def main() -> int:
    print(json.dumps(validate_causal_bundle(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
