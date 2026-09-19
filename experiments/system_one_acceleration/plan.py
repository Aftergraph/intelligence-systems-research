"""Deterministic run-plan expansion for JAR-EXP-0014."""

from dataclasses import dataclass
import json
from pathlib import Path
import random


@dataclass(frozen=True)
class PlannedRun:
    run_id: str
    arm: str
    family: str
    source_workload_id: str
    replicate: int


def _slug(value: str) -> str:
    return (
        value.lower()
        .replace("/", "-")
        .replace(" ", "-")
        .replace("_", "-")
    )


def build_run_plan(workload_path: Path, randomization_path: Path) -> list[PlannedRun]:
    workload = json.loads(Path(workload_path).read_text(encoding="utf-8"))
    randomization = json.loads(Path(randomization_path).read_text(encoding="utf-8"))
    if workload.get("status") != "FROZEN_PRECALIBRATION":
        raise ValueError("workload plan is not frozen")
    if randomization.get("status") != "FROZEN_PRECALIBRATION":
        raise ValueError("randomization spec is not frozen")

    rows: list[PlannedRun] = []
    for arm in sorted(workload["arms"]):
        for family in workload["families"]:
            source_ids = family["source_workloads"]
            counts = family["replication_counts"]
            if len(source_ids) != len(counts):
                raise ValueError("source_workloads/replication_counts mismatch")
            for source_id, count in zip(source_ids, counts, strict=True):
                for replicate in range(1, count + 1):
                    rows.append(
                        PlannedRun(
                            run_id=(
                                f"J14-{arm}-{_slug(family['name'])}-"
                                f"{source_id}-R{replicate:02d}"
                            ),
                            arm=arm,
                            family=family["name"],
                            source_workload_id=source_id,
                            replicate=replicate,
                        )
                    )

    expected = randomization["expected_total_runs"]
    if len(rows) != expected or len({row.run_id for row in rows}) != expected:
        raise ValueError("expanded run plan does not match frozen total")

    rng = random.Random(randomization["seed"])
    rng.shuffle(rows)
    return rows
