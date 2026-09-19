#!/usr/bin/env python3
"""Zero-network falsification verifier for active JAR-EXP-0015 analysis isolation."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.system_one_acceleration.jar15_analysis import (
    DecisionObservation,
    JAR15AnalysisError,
    inference_inputs,
    select_calibration_policy,
    verify_frozen_policy,
)

DATASET = json.loads((ROOT / "data" / "jar_exp_0015_dataset_v03.json").read_text(encoding="utf-8"))
PROTOCOL = json.loads((ROOT / "data" / "jar_exp_0015_protocol_v05.json").read_text(encoding="utf-8"))
GATE = json.loads((ROOT / "data" / "jar_exp_0015_analysis_gate_v01.json").read_text(encoding="utf-8"))


def require(name, condition):
    if not condition:
        raise SystemExit(f"FAIL[{name}]")
    print(f"check={name}:PASS")


def obs(split):
    return [
        DecisionObservation(
            case_id=row["case_id"],
            decision_type=row["decision_type"],
            effective_confidence=0.99,
            correct=True,
            critical=bool(row["critical"]),
        )
        for row in DATASET["cases"]
        if row["split"] == split
    ]


def main():
    cal = obs("calibration")
    hold = obs("holdout")

    require("01_protocol_v05", PROTOCOL["schema_version"] == "jar-exp-0015.protocol/0.5")
    require("02_dataset_v03", DATASET["schema_version"] == "jar-exp-0015.dataset/0.3")
    require("03_calibration_count", len(cal) == 1952)
    require("04_holdout_count", len(hold) == 1952)
    require(
        "05_holdout_inputs_hide_labels",
        all(set(row) == {"case_id", "decision_type", "state"} for row in inference_inputs(DATASET, split="holdout")),
    )

    missing_blocked = False
    try:
        select_calibration_policy(cal[:-1], dataset=DATASET, protocol=PROTOCOL)
    except JAR15AnalysisError:
        missing_blocked = True
    require("06_missing_calibration_blocked", missing_blocked)

    leaked = cal[:-1] + [hold[0]]
    leak_blocked = False
    try:
        select_calibration_policy(leaked, dataset=DATASET, protocol=PROTOCOL)
    except JAR15AnalysisError:
        leak_blocked = True
    require("07_holdout_leak_blocked", leak_blocked)

    policy = select_calibration_policy(cal, dataset=DATASET, protocol=PROTOCOL)
    verify_frozen_policy(policy, PROTOCOL)
    require("08_policy_frozen", policy["status"] == "FROZEN_PREHOLDOUT")
    require("09_policy_binds_1952", policy["calibration_observation_count"] == 1952)
    require("10_policy_protocol_v05", policy["protocol_version"] == "jar-exp-0015.protocol/0.5")
    require("11_policy_does_not_consume_holdout", policy["holdout_consumed"] is False)
    require("12_policy_hash_present", len(policy["policy_sha256"]) == 64)
    require("13_eight_per_type_policies", len(policy["per_decision_type"]) == 8)

    tampered = json.loads(json.dumps(policy))
    tampered["holdout_consumed"] = True
    tamper_blocked = False
    try:
        verify_frozen_policy(tampered, PROTOCOL)
    except JAR15AnalysisError:
        tamper_blocked = True
    require("14_policy_tamper_blocked", tamper_blocked)

    require("15_gate_protocol_v05", GATE["active_protocol_ref"] == "data/jar_exp_0015_protocol_v05.json")
    require("16_gate_calibration_not_run", GATE["status"] == "CALIBRATION_NOT_RUN")
    require("17_holdout_not_authorized", GATE["holdout_evaluation_authorized"] is False)
    require("18_network_not_authorized", GATE["network_calls_authorized"] is False)

    print("PASS: JAR-EXP-0015 analysis isolation verifier")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
