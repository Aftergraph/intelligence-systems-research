#!/usr/bin/env python3
"""Independent zero-network verifier for the frozen JAR-EXP-0015 dataset."""

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.system_one_acceleration.corpus import build_calibration_corpus
from experiments.system_one_acceleration.jar15_dataset import (
    build_split_manifest,
    dataset_document,
    semantic_case_hash,
)

DATASET = ROOT / "data" / "jar_exp_0015_dataset_v01.json"
MANIFEST = ROOT / "data" / "jar_exp_0015_split_manifest_v01.json"
PROTOCOL = ROOT / "data" / "jar_exp_0015_protocol_v01.json"

EXPECTED_DATASET_SHA = "de90286586397af21a568a91c4cd4ec4d56ccfd8a7db09fbd2d7167f6541fac9"
EXPECTED_MANIFEST_SHA = "185f5ca9ed25286fb3c60092f83357e0493038338b08bbdd9b4251c9f01707d1"


def require(name: str, condition: bool) -> None:
    if not condition:
        raise SystemExit(f"FAIL[{name}]")
    print(f"check={name}:PASS")


def main() -> int:
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))

    dataset_sha = sha256(DATASET.read_bytes()).hexdigest()
    manifest_sha = sha256(MANIFEST.read_bytes()).hexdigest()

    require("01_dataset_sha", dataset_sha == EXPECTED_DATASET_SHA)
    require("02_manifest_sha", manifest_sha == EXPECTED_MANIFEST_SHA)
    require("03_protocol_dataset_binding", protocol["dataset"]["dataset_sha256"] == dataset_sha)
    require("04_protocol_manifest_binding", protocol["dataset"]["split_manifest_sha256"] == manifest_sha)
    require("05_generator_dataset_parity", dataset == dataset_document())
    require("06_generator_manifest_parity", manifest == build_split_manifest())

    rows = dataset["cases"]
    require("07_total_cases", len(rows) == 320)
    splits = Counter(row["split"] for row in rows)
    require("08_global_split", splits == {"calibration": 192, "holdout": 128})

    by_type = defaultdict(Counter)
    for row in rows:
        by_type[row["decision_type"]][row["split"]] += 1
    require(
        "09_per_type_split",
        len(by_type) == 8
        and all(counts == {"calibration": 24, "holdout": 16} for counts in by_type.values()),
    )

    ids = [row["case_id"] for row in rows]
    require("10_unique_ids", len(ids) == len(set(ids)) == 320)

    child_hashes = {
        semantic_case_hash(
            decision_type=row["decision_type"],
            state=row["state"],
            expected=row["expected"],
            critical=row["critical"],
        )
        for row in rows
    }
    require("11_unique_semantics", len(child_hashes) == 320)

    parent_hashes = {
        semantic_case_hash(
            decision_type=row.decision_type,
            state=row.state,
            expected=row.expected,
            critical=row.critical,
        )
        for row in build_calibration_corpus()
    }
    require("12_parent_count", len(parent_hashes) == 158)
    require("13_no_parent_duplicate", parent_hashes.isdisjoint(child_hashes))

    authority_critical = {
        decision_type: [
            row
            for row in rows
            if row["decision_type"] == decision_type and row["critical"]
        ]
        for decision_type in ("needs_human", "risk_level")
    }
    require(
        "14_authority_critical_coverage",
        all(len(values) >= 8 for values in authority_critical.values()),
    )
    require(
        "15_authority_critical_split",
        all(
            {"calibration", "holdout"}.issubset({row["split"] for row in values})
            for values in authority_critical.values()
        ),
    )

    manifest_by_id = {entry["case_id"]: entry for entry in manifest["cases"]}
    require("16_manifest_cardinality", len(manifest_by_id) == 320)
    require(
        "17_manifest_no_labels_or_state",
        all("expected" not in entry and "state" not in entry for entry in manifest["cases"]),
    )
    require(
        "18_manifest_semantic_binding",
        all(
            manifest_by_id[row["case_id"]]["semantic_sha256"]
            == semantic_case_hash(
                decision_type=row["decision_type"],
                state=row["state"],
                expected=row["expected"],
                critical=row["critical"],
            )
            for row in rows
        ),
    )
    require("19_parent_duplicate_counter", manifest["exact_parent_duplicates"] == 0)
    require("20_network_fail_closed", protocol["network_calls_authorized"] is False)

    print("PASS: JAR-EXP-0015 frozen dataset verifier")
    print(f"dataset_sha256={dataset_sha}")
    print(f"split_manifest_sha256={manifest_sha}")
    print("cases=320 calibration=192 holdout=128 parent_duplicates=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
