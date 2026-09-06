from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import yaml

CONDITIONS = ("A", "B", "C", "D")
DEFAULT_TRACE = Path(__file__).with_name("workloads") / "trace_replay.yaml"


def _validated_trace(trace: dict) -> tuple[str, int, list[dict]]:
    if not isinstance(trace, dict):
        raise ValueError("trace must be a mapping")

    trace_id = trace.get("trace_id")
    if not isinstance(trace_id, str) or not trace_id.strip():
        raise ValueError("trace_id is required")

    revision = trace.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ValueError("trace revision must be an integer >= 1")

    steps = trace.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("trace steps must be a non-empty list")
    if not all(isinstance(step, dict) and step.get("operation") for step in steps):
        raise ValueError("each trace step must be a mapping with an operation")

    return trace_id.strip(), revision, [dict(step) for step in steps]


def build_trace_measurement_plan(
    trace: dict,
    *,
    repetitions: int = 20,
    seed: int = 130013,
) -> dict:
    """Build a deterministic paired A/B/C/D trace-replay schedule.

    This function only creates the preregistered execution order. It does not run a
    treatment and therefore is not performance evidence.
    """
    if not isinstance(repetitions, int) or isinstance(repetitions, bool) or repetitions < 1:
        raise ValueError("repetitions must be an integer >= 1")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")

    trace_id, revision, steps = _validated_trace(trace)
    rng = random.Random(seed)
    runs: list[dict] = []
    sequence = 0

    for pair_number in range(1, repetitions + 1):
        pair_conditions = list(CONDITIONS)
        rng.shuffle(pair_conditions)
        pair_id = f"{trace_id}-pair-{pair_number:03d}"
        for condition in pair_conditions:
            sequence += 1
            runs.append(
                {
                    "sequence": sequence,
                    "pair_id": pair_id,
                    "condition": condition,
                    "trace_id": trace_id,
                    "trace_revision": revision,
                }
            )

    return {
        "experiment_id": "JAR-EXP-0013",
        "phase": "TRACE_REPLAY",
        "plan_only": True,
        "performance_evidence": False,
        "seed": seed,
        "repetitions": repetitions,
        "conditions": list(CONDITIONS),
        "trace": {
            "trace_id": trace_id,
            "revision": revision,
            "steps": steps,
        },
        "runs": runs,
    }


def write_measurement_plan(path: str | Path, plan: dict) -> Path:
    """Write one immutable plan and refuse to overwrite an existing artifact."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(plan, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return output


def load_trace(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("trace workload must be a YAML mapping")
    _validated_trace(payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the preregistered JAR-EXP-0013 paired trace-replay plan"
    )
    parser.add_argument("--trace", default=str(DEFAULT_TRACE), help="Trace workload YAML")
    parser.add_argument("--output", required=True, help="New JSON plan path; overwrite is refused")
    parser.add_argument("--repetitions", type=int, default=20)
    parser.add_argument("--seed", type=int, default=130013)
    args = parser.parse_args(argv)

    plan = build_trace_measurement_plan(
        load_trace(args.trace),
        repetitions=args.repetitions,
        seed=args.seed,
    )
    output = write_measurement_plan(args.output, plan)
    print(
        json.dumps(
            {
                "experiment_id": plan["experiment_id"],
                "phase": plan["phase"],
                "pairs": plan["repetitions"],
                "runs": len(plan["runs"]),
                "seed": plan["seed"],
                "output": str(output),
                "performance_evidence": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
