"""Content-addressed integrity manifest for JAR-EXP-0015 calibration authorization.

This manifest is separate from the JAR-EXP-0014 calibration manifest so the
frozen 0014 record is never disturbed by 0015 execution-path changes.

The calibration gate is deliberately EXCLUDED from the path list, mirroring the
0014 design: the gate pins this manifest's hash, so including the gate here would
create a hash cycle. The gate is therefore the tamper-evident consumer of the
manifest, not a member of it.
"""

from pathlib import Path

from .integrity import content_manifest_sha256


JAR15_CALIBRATION_INTEGRITY_PATHS = (
    "experiments/system_one_acceleration/adapter.py",
    "experiments/system_one_acceleration/calibration.py",
    "experiments/system_one_acceleration/calibration_runner.py",
    "experiments/system_one_acceleration/client.py",
    "experiments/system_one_acceleration/corpus.py",
    "experiments/system_one_acceleration/cost_guard.py",
    "experiments/system_one_acceleration/durable_calibration.py",
    "experiments/system_one_acceleration/guarded_jar15_calibration.py",
    "experiments/system_one_acceleration/jar15_analysis.py",
    "experiments/system_one_acceleration/jar15_calibration_preflight.py",
    "experiments/system_one_acceleration/jar15_dataset.py",
    "experiments/system_one_acceleration/jar15_dataset_v03.py",
    "experiments/system_one_acceleration/jar15_integrity.py",
    "experiments/system_one_acceleration/jar15_pricing.py",
    "experiments/system_one_acceleration/jar15_receipt.py",
    "experiments/system_one_acceleration/protocol.py",
    "experiments/system_one_acceleration/state_projection.py",
    "data/jar_exp_0015_active_protocol.json",
    "data/jar_exp_0015_protocol_v04.json",
    "data/jar_exp_0015_dataset_v03.json",
    "data/jar_exp_0015_split_manifest_v03.json",
    "data/jar_exp_0015_question_contracts_v01.json",
    "data/jar_exp_0015_typesafe_pricing_v01.json",
    "requirements-typesafe.txt",
    "schemas/jar-exp-0015-dataset.v0.3.json",
    "schemas/jar-exp-0015-split-manifest.v0.3.json",
    "schemas/jar-exp-0015-policy.v0.1.json",
    "schemas/jar-exp-0015-calibration-receipt.v0.1.json",
    "scripts/run_jar_exp_0015_live_calibration.py",
    "scripts/verify_jar_exp_0015_semantic_review.py",
)


def jar15_calibration_manifest_sha256(root: Path) -> str:
    return content_manifest_sha256(root, JAR15_CALIBRATION_INTEGRITY_PATHS)