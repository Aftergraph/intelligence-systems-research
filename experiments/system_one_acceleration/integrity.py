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
    "experiments/system_one_acceleration/cost_guard.py",
    "experiments/system_one_acceleration/durable_calibration.py",
    "experiments/system_one_acceleration/guarded_calibration.py",
    "experiments/system_one_acceleration/integrity.py",
    "experiments/system_one_acceleration/protocol.py",
    "experiments/system_one_acceleration/state_projection.py",
    "data/jar_exp_0014_calibration_protocol_v01.json",
    "data/jar_exp_0014_question_contracts_v01.json",
    "data/jar_exp_0014_typesafe_pricing_v01.json",
    "requirements-typesafe.txt",
    "schemas/system-one-calibration-approval-receipt.v0.1.json",
    "schemas/system-one-calibration-receipt.v0.1.json",
    "schemas/system-one-pricing-spec.v0.1.json",
    "schemas/system-one-semantic-review-receipt.v0.1.json",
    "scripts/verify_jar_exp_0014_semantic_review.py",
    "scripts/run_jar_exp_0014_live_calibration.py",
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


EXECUTION_STATIC_PATHS = (
    "data/jar_exp_0014_question_contracts_v01.json",
    "data/jar_exp_0014_workload_plan_v01.json",
    "data/jar_exp_0014_critical_risk_pack_v01.json",
    "data/jar_exp_0014_randomization_v01.json",
    "data/jar_exp_0014_calibration_protocol_v01.json",
    "data/jar_exp_0014_typesafe_pricing_v01.json",
    "requirements-typesafe.txt",
    "schemas/system-one-calibration-receipt.v0.1.json",
    "schemas/system-one-decision-receipt.v0.1.json",
    "schemas/system-one-execution-approval-receipt.v0.1.json",
    "schemas/system-one-pricing-spec.v0.1.json",
)


def execution_manifest_sha256(root: Path) -> str:
    root = Path(root).resolve()
    module_dir = root / "experiments" / "system_one_acceleration"
    module_paths = tuple(
        path.relative_to(root).as_posix()
        for path in sorted(module_dir.glob("*.py"))
    )
    return content_manifest_sha256(root, (*EXECUTION_STATIC_PATHS, *module_paths))


JAR15_CALIBRATION_INTEGRITY_PATHS = (
    "data/jar_exp_0015_active_protocol.json",
    "data/jar_exp_0015_protocol_v04.json",
    "data/jar_exp_0015_dataset_v03.json",
    "data/jar_exp_0015_split_manifest_v03.json",
    "data/jar_exp_0015_typesafe_pricing_v01.json",
    "experiments/system_one_acceleration/jar15_analysis.py",
    "experiments/system_one_acceleration/jar15_cost_guard.py",
    "experiments/system_one_acceleration/jar15_dataset_v03.py",
    "experiments/system_one_acceleration/jar15_preflight.py",
    "experiments/system_one_acceleration/state_projection.py",
    "experiments/system_one_acceleration/calibration.py",
    "experiments/system_one_acceleration/cost_guard.py",
    "schemas/jar-exp-0015-dataset.v0.3.json",
    "schemas/jar-exp-0015-split-manifest.v0.3.json",
    "schemas/jar-exp-0015-policy.v0.1.json",
    "schemas/jar-exp-0015-typesafe-pricing.v0.1.json",
    "schemas/jar-exp-0015-semantic-review-receipt.v0.1.json",
    "scripts/verify_jar_exp_0015_dataset.py",
    "scripts/verify_jar_exp_0015_analysis.py",
    "scripts/verify_jar_exp_0015_cost_gate.py",
    "scripts/verify_jar_exp_0015_semantic_review.py",
)


def jar15_calibration_manifest_sha256(root: Path) -> str:
    return content_manifest_sha256(root, JAR15_CALIBRATION_INTEGRITY_PATHS)
