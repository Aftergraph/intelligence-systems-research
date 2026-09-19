#!/usr/bin/env python3
"""Execute the bounded JAR-EXP-0014 live calibration and persist evidence atomically."""

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.system_one_acceleration.calibration_preflight import evaluate_calibration_preflight
from experiments.system_one_acceleration.calibration_receipt import build_calibration_receipt
from experiments.system_one_acceleration.client import load_frozen_contracts
from experiments.system_one_acceleration.corpus import build_calibration_corpus
from experiments.system_one_acceleration.guarded_calibration import run_authorized_calibration
from experiments.system_one_acceleration.integrity import calibration_manifest_sha256


RUN_ID = "jar-exp-0014-calibration-20260919-v01"
FINAL_DIR = ROOT / "data" / "jar_exp_0014_calibration_live_20260919"


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
        "schema_version": "jar-exp-0014.calibration-run-summary/0.1",
        "experiment_id": "JAR-EXP-0014",
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
    manifest_sha = calibration_manifest_sha256(ROOT)
    preflight = evaluate_calibration_preflight(ROOT)
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
    contracts = load_frozen_contracts(
        ROOT / "data" / "jar_exp_0014_question_contracts_v01.json"
    )
    cases = build_calibration_corpus()
    result = run_authorized_calibration(
        root=ROOT,
        client=client,
        sdk=sdk,
        contracts=contracts,
    )

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    protocol = json.loads(
        (ROOT / "data" / "jar_exp_0014_calibration_protocol_v01.json").read_text(
            encoding="utf-8"
        )
    )
    receipt = build_calibration_receipt(
        receipt_id=RUN_ID,
        result=result,
        cases=cases,
        protocol_document=protocol,
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
