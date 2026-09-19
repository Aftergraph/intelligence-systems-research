#!/usr/bin/env python3
"""Independent zero-network verifier for active JAR-EXP-0015 protocol/data."""

from collections import Counter, defaultdict
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.system_one_acceleration.calibration import wilson_upper
from experiments.system_one_acceleration.corpus import build_calibration_corpus
from experiments.system_one_acceleration.jar15_dataset import semantic_case_hash
from experiments.system_one_acceleration.jar15_dataset_v02 import (
    build_prospective_dataset_v02,
    dataset_document_v02,
    split_manifest_v02,
)

ACTIVE = ROOT / "data" / "jar_exp_0015_active_protocol.json"
PROTOCOL = ROOT / "data" / "jar_exp_0015_protocol_v03.json"
DATASET = ROOT / "data" / "jar_exp_0015_dataset_v02.json"
MANIFEST = ROOT / "data" / "jar_exp_0015_split_manifest_v02.json"

EXPECTED_DATASET_SHA = "690a28874f409a7624d371374637c0421ef6008179eba68fdc8a02a8d539bc9d"
EXPECTED_MANIFEST_SHA = "9821b7513dee79d092ffd999e4848099c8b676529687b689b573ce02e5093dac"


def require(name: str, condition: bool) -> None:
    if not condition:
        raise SystemExit(f"FAIL[{name}]")
    print(f"check={name}:PASS")


def git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    return sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def main() -> int:
    active = json.loads(ACTIVE.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    dataset_sha = sha256(DATASET.read_bytes()).hexdigest()
    manifest_sha = sha256(MANIFEST.read_bytes()).hexdigest()

    require("01_active_protocol", active["active_protocol_ref"] == "data/jar_exp_0015_protocol_v03.json")
    require("02_protocol_blob_binding", active["active_protocol_git_blob_sha"] == git_blob_sha(PROTOCOL))
    require("03_dataset_sha", dataset_sha == EXPECTED_DATASET_SHA == active["active_dataset_sha256"])
    require("04_manifest_sha", manifest_sha == EXPECTED_MANIFEST_SHA == active["active_split_manifest_sha256"])
    require("05_protocol_dataset_binding", protocol["dataset"]["dataset_sha256"] == dataset_sha)
    require("06_protocol_manifest_binding", protocol["dataset"]["split_manifest_sha256"] == manifest_sha)
    require("07_generator_dataset_parity", dataset == dataset_document_v02())
    require("08_generator_manifest_parity", manifest == split_manifest_v02())

    rows = dataset["cases"]
    require("09_total_cases", len(rows) == 3904)
    require("10_global_split", Counter(r["split"] for r in rows) == {"calibration": 1952, "holdout": 1952})

    by_type = defaultdict(Counter)
    for row in rows:
        by_type[row["decision_type"]][row["split"]] += 1
    require(
        "11_per_type_split",
        len(by_type) == 8
        and all(c == {"calibration": 244, "holdout": 244} for c in by_type.values()),
    )

    ids = [row["case_id"] for row in rows]
    require("12_unique_ids", len(ids) == len(set(ids)) == 3904)

    child_hashes = {
        semantic_case_hash(
            decision_type=r["decision_type"],
            state=r["state"],
            expected=r["expected"],
            critical=r["critical"],
        )
        for r in rows
    }
    require("13_unique_semantics", len(child_hashes) == 3904)

    parent_hashes = {
        semantic_case_hash(
            decision_type=r.decision_type,
            state=r.state,
            expected=r.expected,
            critical=r.critical,
        )
        for r in build_calibration_corpus()
    }
    require("14_parent_count", len(parent_hashes) == 158)
    require("15_no_parent_duplicate", parent_hashes.isdisjoint(child_hashes))

    require("16_v01_wilson_falsified", wilson_upper(0, 24) > 0.05 and wilson_upper(0, 16) > 0.05)
    require("17_minimum_wilson_n", wilson_upper(0, 72) > 0.05 and wilson_upper(0, 73) <= 0.05)
    require("18_v03_coverage_rounding", math.ceil(244 * 0.30) == 74 and protocol["sample_size_feasibility"]["floor_accepted_n_at_30_percent"] == 74)
    require("19_v03_zero_error_feasible", wilson_upper(0, 74) <= 0.05)
    require("20_network_fail_closed", protocol["network_calls_authorized"] is False and active["network_calls_authorized"] is False)

    superseded = {x["protocol_ref"] for x in active["superseded"]}
    require(
        "21_superseded_protocols",
        superseded == {"data/jar_exp_0015_protocol_v01.json", "data/jar_exp_0015_protocol_v02.json"},
    )
    require("22_manifest_parent_duplicate_counter", manifest["exact_parent_duplicates"] == 0)

    critical_by_type = {
        dtype: [r for r in rows if r["decision_type"] == dtype and r["critical"]]
        for dtype in ("needs_human", "risk_level")
    }
    require("23_authority_critical_count", all(len(v) >= 8 for v in critical_by_type.values()))
    require("24_authority_critical_split", all({r["split"] for r in v} == {"calibration", "holdout"} for v in critical_by_type.values()))

    print("PASS: active JAR-EXP-0015 dataset/protocol verifier")
    print("active_protocol=v0.3 dataset=v0.2")
    print(f"dataset_sha256={dataset_sha}")
    print(f"split_manifest_sha256={manifest_sha}")
    print("cases=3904 calibration=1952 holdout=1952 parent_duplicates=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
