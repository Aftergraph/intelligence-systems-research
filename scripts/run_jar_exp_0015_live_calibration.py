#!/usr/bin/env python3
"""Execute the bounded JAR-EXP-0015 live calibration and persist evidence atomically.

This entrypoint is fail-closed. It performs zero network access unless the
deterministic preflight returns READY_TO_CALIBRATE, which requires a frozen
calibration-manifest pin, a content-addressed semantic review, and an explicit
owner/network approval. The owner/network approval is a human step; absent it,
live execution raises before any provider call is made.
"""

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.system_one_acceleration.client import load_frozen_contracts
from experiments.system_one_acceleration.guarded_jar15_calibration import (
    jar15_calibration_cases,
    run_authorized_jar15_calibration,
)
from experiments.system_one_acceleration.jar15_calibration_preflight import (
    evaluate_jar15_calibration_preflight,
)
from experiments.system_one_acceleration.jar15_integrity import (
    jar15_calibration_manifest_sha256,
)
from experiments.system_one_acceleration.jar15_receipt import (
    build_jar15_calibration_receipt,
)


RUN_ID = "jar-exp-0015-calibration-20260920-v04"
FINAL_DIR = ROOT / "data" / "jar_exp_0015_calibration_live_20260920"
DATASET_REF = "data/jar_exp_0015_dataset_v03.json"
SPLIT_MANIFEST_REF = "data/jar_exp_0015_split_manifest_v03.json"
PROTOCOL_REF = "data/jar_exp_0015_protocol_v04.json"
CONTRACTS_REF = "data/jar_exp_0015_question_contracts_v01.json"


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _atomic_result_dir(result, receipt, manifest_sha: str, source_commit: str) -> Path:
    tmp = FINAL_DIR.with_name(FINAL_DIR.name + ".tmp")
    if FINAL_DIR.exists():
        raise RuntimeError(f"final calibration evidence already exists: {FINAL_DIR}")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    observations_path = tmp / "observations.jsonl"
    with observations_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in result.observations:
            handle.write(
                json.dumps(
                    asdict(row),
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                )
                + "\n"
            )
        handle.flush()
        os.fsync(handle.fileno())

    receipt_path = tmp / "CALIBRATION-RECEIPT.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    summary = {
        "schema_version": "jar-exp-0015.calibration-run-summary/0.1",
        "experiment_id": "JAR-EXP-0015",
        "run_id": RUN_ID,
        "source_commit": source_commit,
        "calibration_manifest_sha256": manifest_sha,
        "provider_calls": result.provider_calls,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "returned_model": result.returned_model,
        "threshold": asdict(result.threshold),
        "observation_count": len(result.observations),
    }
    (tmp / "RUN-SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, FINAL_DIR)
    return FINAL_DIR


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()

    source_commit = _git_head()
    manifest_sha = jar15_calibration_manifest_sha256(ROOT)
    preflight = evaluate_jar15_calibration_preflight(ROOT)
    print(f"HEAD={source_commit}")
    print(f"CAL_MANIFEST={manifest_sha}")
    print(f"DECISION={preflight.decision}")
    print("BLOCKERS=" + "|".join(preflight.blockers))
    print(f"MODEL={preflight.requested_model}")
    print(f"MAX_CALLS={preflight.maximum_calls}")
    print(f"MAX_COST={preflight.maximum_cost_usd}")

    if preflight.decision != "READY_TO_CALIBRATE":
        return 2
    if args.preflight_only:
        return 0

    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        raise RuntimeError("TYPESAFE_API_KEY is required for live calibration")

    import typesafe_sdk as sdk

    client = sdk.TypeSafeClient(api_key=api_key)
    contracts = load_frozen_contracts(ROOT / CONTRACTS_REF)
    cases = jar15_calibration_cases(ROOT)
    result = run_authorized_jar15_calibration(
        root=ROOT,
        client=client,
        sdk=sdk,
        contracts=contracts,
    )

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    protocol = json.loads((ROOT / PROTOCOL_REF).read_text(encoding="utf-8"))
    dataset_sha = sha256((ROOT / DATASET_REF).read_bytes()).hexdigest()
    manifest_sha_split = sha256((ROOT / SPLIT_MANIFEST_REF).read_bytes()).hexdigest()
    receipt = build_jar15_calibration_receipt(
        receipt_id=RUN_ID,
        result=result,
        cases=cases,
        protocol_document=protocol,
        dataset_sha256=dataset_sha,
        split_manifest_sha256=manifest_sha_split,
        calibration_manifest_sha256=manifest_sha,
        source_commit=source_commit,
        generated_at=generated_at,
    )
    output = _atomic_result_dir(result, receipt, manifest_sha, source_commit)
    print(f"RESULT_DIR={output}")
    print(f"PROVIDER_CALLS={result.provider_calls}")
    print(f"INPUT_TOKENS={result.input_tokens}")
    print(f"OUTPUT_TOKENS={result.output_tokens}")
    print(f"RETURNED_MODEL={result.returned_model}")
    print(f"THRESHOLD={result.threshold.threshold}")
    print(f"FEASIBLE={result.threshold.feasible}")
    print(f"ACCEPTED={result.threshold.accepted}")
    print(f"ERRORS={result.threshold.errors}")
    print(f"CRITICAL_ERRORS={result.threshold.critical_errors}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())