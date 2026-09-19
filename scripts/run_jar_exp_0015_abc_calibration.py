#!/usr/bin/env python3
"""Execute authorized JAR-EXP-0015 A/B/C calibration and persist evidence."""

from dataclasses import asdict
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.system_one_acceleration.integrity import (
    jar15_calibration_manifest_sha256,
)
from experiments.system_one_acceleration.jar15_live import (
    run_authorized_jar15_abc_calibration,
)
from experiments.system_one_acceleration.jar15_preflight import (
    evaluate_jar15_stage_preflight,
)


FINAL_DIR = ROOT / "data" / "jar_exp_0015_abc_calibration_live"
RUN_ID = "JAR-EXP-0015-A-B-C-calibration-v01"


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _write_atomic(result, policy, manifest_sha: str, source_commit: str) -> Path:
    if FINAL_DIR.exists():
        raise RuntimeError(f"final evidence already exists: {FINAL_DIR}")
    tmp = FINAL_DIR.with_name(FINAL_DIR.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    with (tmp / "observations.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
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

    (tmp / "FROZEN-PREHOLDOUT-POLICY.json").write_text(
        json.dumps(policy, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary = {
        "schema_version": "jar-exp-0015.abc-calibration-run-summary/0.1",
        "experiment_id": "JAR-EXP-0015",
        "run_id": RUN_ID,
        "stage": "A_B_C_ORIGINAL_CONTRACT_CALIBRATION",
        "source_commit": source_commit,
        "calibration_manifest_sha256": manifest_sha,
        "provider_calls": result.provider_calls,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "returned_model": result.returned_model,
        "global_threshold": asdict(result.threshold),
        "policy_sha256": policy["policy_sha256"],
        "holdout_consumed": False,
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
    manifest = jar15_calibration_manifest_sha256(ROOT)
    preflight = evaluate_jar15_stage_preflight(ROOT, stage="calibration")
    print(f"HEAD={source_commit}")
    print(f"CAL_MANIFEST={manifest}")
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
        raise RuntimeError("TYPESAFE_API_KEY is required")

    import typesafe_sdk as sdk

    client = sdk.TypeSafeClient(api_key=api_key)
    result, policy = run_authorized_jar15_abc_calibration(
        root=ROOT,
        client=client,
        sdk=sdk,
    )
    output = _write_atomic(result, policy, manifest, source_commit)
    print(f"RESULT_DIR={output}")
    print(f"PROVIDER_CALLS={result.provider_calls}")
    print(f"INPUT_TOKENS={result.input_tokens}")
    print(f"OUTPUT_TOKENS={result.output_tokens}")
    print(f"RETURNED_MODEL={result.returned_model}")
    print(f"POLICY_SHA256={policy['policy_sha256']}")
    print(f"GLOBAL_FEASIBLE={policy['global_threshold']['feasible']}")
    print("FALLBACK_TYPES=" + "|".join(policy["selective_cascade"]["fallback_decision_types"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
