from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Callable

import yaml

from .evidence import write_run_evidence
from .host_preflight import check_preflight
from .protocol import load_protocol
from .verification.differential import compare_observable

_EXPECTED_CONDITIONS = ("A", "B")


def _require_mapping(value, label: str) -> dict:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a mapping")
    return value


def _write_json_exclusive(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def build_tool_microbench_plan(workload: dict, protocol: dict) -> dict:
    """Freeze the paired A/B schedule for the preregistered tool microbenchmark phase."""
    workload = _require_mapping(workload, "workload")
    protocol = _require_mapping(protocol, "protocol")
    if protocol.get("experiment_id") != "JAR-EXP-0013":
        raise ValueError("unexpected JAR-EXP-0013 protocol identity")

    workload_id = workload.get("workload_id")
    if not isinstance(workload_id, str) or not workload_id.strip():
        raise ValueError("tool microbenchmark workload_id must be non-empty")

    operations = workload.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ValueError("tool microbenchmark operations must be a non-empty list")
    if any(not isinstance(operation, str) or not operation.strip() for operation in operations):
        raise ValueError("tool microbenchmark operation names must be non-empty strings")
    if len(set(operations)) != len(operations):
        raise ValueError("tool microbenchmark operation names must be unique")

    confirmatory = _require_mapping(protocol.get("confirmatory"), "protocol confirmatory")
    if confirmatory.get("run_order") != "randomized_within_paired_blocks":
        raise ValueError("tool microbenchmark requires randomized_within_paired_blocks")
    minimum_warm = int(confirmatory["minimum_microbenchmark_warm_repetitions"])
    warm_repetitions = int(workload.get("warm_repetitions", 0))
    if warm_repetitions < minimum_warm:
        raise ValueError(
            f"tool microbenchmark warm repetitions must be >= protocol minimum {minimum_warm}"
        )

    analysis = _require_mapping(protocol.get("analysis"), "protocol analysis")
    seed = int(analysis["bootstrap_seed"])
    rng = random.Random(seed)

    runs: list[dict] = []
    sequence = 0
    pair_count = 0
    for operation in operations:
        samples = [("cold", 0)] + [
            ("warm", repetition) for repetition in range(1, warm_repetitions + 1)
        ]
        for sample_kind, repetition in samples:
            pair_count += 1
            pair_id = f"{operation}-{sample_kind}-{repetition:02d}"
            condition_order = list(_EXPECTED_CONDITIONS)
            rng.shuffle(condition_order)
            for condition in condition_order:
                sequence += 1
                runs.append(
                    {
                        "sequence": sequence,
                        "pair_id": pair_id,
                        "condition": condition,
                        "operation": operation,
                        "sample_kind": sample_kind,
                        "repetition": repetition,
                    }
                )

    return {
        "experiment_id": "JAR-EXP-0013",
        "phase": "TOOL_MICROBENCH",
        "workload_id": workload_id,
        "conditions": list(_EXPECTED_CONDITIONS),
        "seed": seed,
        "warm_repetitions": warm_repetitions,
        "paired_blocks": pair_count,
        "planned_runs": len(runs),
        "plan_only": True,
        "performance_evidence": False,
        "runs": runs,
    }


def write_tool_microbench_plan(path: str | Path, plan: dict) -> None:
    _write_json_exclusive(Path(path), _require_mapping(plan, "plan"))


def _validate_execution_contract(
    plan: dict, protocol: dict, host_probe: dict
) -> list[tuple[str, list[dict]]]:
    plan = _require_mapping(plan, "plan")
    protocol = _require_mapping(protocol, "protocol")
    host_probe = _require_mapping(host_probe, "host probe")

    if (
        host_probe.get("experiment_id") != "JAR-EXP-0013"
        or host_probe.get("state") != "READY"
    ):
        raise ValueError(
            "Phase-2 tool microbenchmark requires a JAR-EXP-0013 controlled host in READY state"
        )
    if (
        plan.get("experiment_id") != "JAR-EXP-0013"
        or protocol.get("experiment_id") != "JAR-EXP-0013"
    ):
        raise ValueError("unexpected JAR-EXP-0013 experiment identity")
    if plan.get("phase") != "TOOL_MICROBENCH" or plan.get("plan_only") is not True:
        raise ValueError("Phase-2 requires the frozen TOOL_MICROBENCH plan")
    if tuple(plan.get("conditions", ())) != _EXPECTED_CONDITIONS:
        raise ValueError("Phase-2 tool microbenchmark conditions must be exactly A/B")

    protocol_conditions = protocol.get("conditions") or {}
    if not isinstance(protocol_conditions, dict):
        raise TypeError("protocol conditions must be a mapping")
    for condition in _EXPECTED_CONDITIONS:
        if condition not in protocol_conditions:
            raise ValueError(f"protocol is missing condition {condition}")
    if protocol_conditions["A"].get("tool_layer") != "stock_hermes":
        raise ValueError("condition A must use stock_hermes")
    if protocol_conditions["B"].get("tool_layer") != "toolrush":
        raise ValueError("condition B must use toolrush")

    protocol_pins = _require_mapping(protocol.get("pins"), "protocol pins")
    probe_pins = _require_mapping(host_probe.get("pins"), "host probe pins")
    expected_pin = str(protocol_pins.get("toolrush", "")).strip().lower()
    observed_pin = str(probe_pins.get("toolrush", "")).strip().lower()
    if not expected_pin or observed_pin != expected_pin:
        raise ValueError("ToolRush pin mismatch between protocol and controlled-host probe")

    runs = plan.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("Phase-2 plan has no runs")
    if [run.get("sequence") for run in runs] != list(range(1, len(runs) + 1)):
        raise ValueError("Phase-2 plan sequence must be contiguous and frozen")

    grouped: dict[str, list[dict]] = {}
    for raw_run in runs:
        run = _require_mapping(raw_run, "run")
        pair_id = run.get("pair_id")
        if not isinstance(pair_id, str) or not pair_id:
            raise ValueError("every Phase-2 run requires a pair_id")
        condition = run.get("condition")
        if condition not in _EXPECTED_CONDITIONS:
            raise ValueError(f"invalid Phase-2 condition: {condition}")
        operation = run.get("operation")
        if not isinstance(operation, str) or not operation:
            raise ValueError("every Phase-2 run requires an operation")
        sample_kind = run.get("sample_kind")
        if sample_kind not in {"cold", "warm"}:
            raise ValueError("Phase-2 sample_kind must be cold or warm")
        repetition = run.get("repetition")
        if not isinstance(repetition, int) or repetition < 0:
            raise ValueError("Phase-2 repetition must be a non-negative integer")
        grouped.setdefault(pair_id, []).append(dict(run))

    pairs = list(grouped.items())
    for pair_id, pair_runs in pairs:
        if len(pair_runs) != 2 or {
            run["condition"] for run in pair_runs
        } != set(_EXPECTED_CONDITIONS):
            raise ValueError(f"paired block {pair_id} must contain A/B exactly once")
        signatures = {
            (run["operation"], run["sample_kind"], run["repetition"])
            for run in pair_runs
        }
        if len(signatures) != 1:
            raise ValueError(f"paired block {pair_id} has mismatched workload identity")

    if int(plan.get("paired_blocks", -1)) != len(pairs):
        raise ValueError("Phase-2 paired_blocks does not match the frozen run schedule")
    if int(plan.get("planned_runs", -1)) != len(runs):
        raise ValueError("Phase-2 planned_runs does not match the frozen run schedule")
    return pairs


def _normalize_result(result: dict) -> dict:
    result = _require_mapping(result, "operation result")
    if "observable" not in result:
        raise ValueError("operation result requires observable")
    elapsed = result.get("elapsed_ms")
    if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)):
        raise ValueError("operation result elapsed_ms must be numeric")
    elapsed = float(elapsed)
    if elapsed < 0.0:
        raise ValueError("operation result elapsed_ms must be >= 0")
    return {
        "observable": result["observable"],
        "elapsed_ms": elapsed,
        "stderr": str(result.get("stderr", "")),
        "error": None,
    }


def _failed_result(exc: Exception) -> dict:
    return {
        "observable": None,
        "elapsed_ms": None,
        "stderr": f"{type(exc).__name__}: {exc}",
        "error": f"{type(exc).__name__}: {exc}",
    }


def _verify(condition: str, result: dict, control: dict | None) -> dict:
    if result.get("error"):
        return {
            "verified": False,
            "classification": "EXECUTION_ERROR",
            "details": {"error": result["error"]},
            "observable": result.get("observable"),
        }
    if condition == "A":
        return {
            "verified": True,
            "classification": "CONTROL_REFERENCE",
            "details": {},
            "observable": result["observable"],
        }
    if control is None or control.get("error"):
        return {
            "verified": False,
            "classification": "CONTROL_UNAVAILABLE",
            "details": {},
            "observable": result["observable"],
        }
    differential = compare_observable(control["observable"], result["observable"])
    return {
        "verified": differential.equal,
        "classification": differential.classification,
        "details": differential.details,
        "observable": result["observable"],
    }


def execute_tool_microbench_plan(
    plan: dict,
    protocol: dict,
    host_probe: dict,
    *,
    evidence_root: str | Path,
    execution_id: str,
    operation_runner: Callable[[str, str, str, int], dict],
    snapshot_provider: Callable[[], dict],
    pair_prepare: Callable[[str, list[dict]], None] | None = None,
) -> dict:
    """Execute frozen A/B tool microbenchmark pairs on an already-READY host.

    ``operation_runner`` owns the real operation timing boundary. This executor owns frozen
    ordering, host cleanliness, differential correctness, and immutable evidence. ``pair_prepare``
    runs before the paired-block preflight snapshot so a host orchestrator can establish the
    exact treatment lifecycle outside the measured interval without contaminating the snapshot.
    No fallback treatment is substituted.
    """
    pairs = _validate_execution_contract(plan, protocol, host_probe)
    if not str(execution_id).strip():
        raise ValueError("execution_id must be non-empty")
    if not callable(operation_runner) or not callable(snapshot_provider):
        raise TypeError("operation_runner and snapshot_provider must be callable")
    if pair_prepare is not None and not callable(pair_prepare):
        raise TypeError("pair_prepare must be callable when provided")

    root = Path(evidence_root)
    root.mkdir(parents=True, exist_ok=True)
    session = root / str(execution_id)
    session.mkdir(parents=False, exist_ok=False)
    (session / "runs").mkdir()
    (session / "blocks").mkdir()

    limits = _require_mapping(protocol.get("preflight"), "protocol preflight")
    run_summaries: list[dict] = []
    excluded_pair_ids: list[str] = []
    clean_pairs = 0
    correctness_failures = 0

    for pair_id, pair_runs in pairs:
        if pair_prepare is not None:
            pair_prepare(pair_id, [dict(run) for run in pair_runs])
        snapshot = dict(snapshot_provider())
        preflight = check_preflight(snapshot, limits)
        representative = pair_runs[0]
        block_state = "CLEAN" if preflight["clean"] else "CONTAMINATED"
        _write_json_exclusive(
            session / "blocks" / f"{pair_id}.json",
            {
                "experiment_id": "JAR-EXP-0013",
                "phase": "TOOL_MICROBENCH",
                "pair_id": pair_id,
                "operation": representative["operation"],
                "sample_kind": representative["sample_kind"],
                "repetition": representative["repetition"],
                "state": block_state,
                "captured_before_treatments": True,
                "snapshot": snapshot,
                "preflight": preflight,
            },
        )
        if not preflight["clean"]:
            excluded_pair_ids.append(pair_id)
            continue

        clean_pairs += 1
        executed: list[tuple[dict, dict]] = []
        for run in pair_runs:
            try:
                result = _normalize_result(
                    operation_runner(
                        run["condition"],
                        run["operation"],
                        run["sample_kind"],
                        run["repetition"],
                    )
                )
            except Exception as exc:
                result = _failed_result(exc)
            executed.append((run, result))

        control = next(
            (result for run, result in executed if run["condition"] == "A"), None
        )
        for run, result in executed:
            condition = run["condition"]
            verifier = _verify(condition, result, control)
            if condition == "B" and verifier["verified"] is not True:
                correctness_failures += 1

            metrics = {"tool_wall_clock_ms": result["elapsed_ms"]}
            metadata = {
                "experiment_id": "JAR-EXP-0013",
                "protocol_revision": protocol.get("revision"),
                "phase": "TOOL_MICROBENCH",
                "execution_id": str(execution_id),
                "workload_id": plan.get("workload_id"),
                "pair_id": pair_id,
                "sequence": run["sequence"],
                "condition": condition,
                "operation": run["operation"],
                "sample_kind": run["sample_kind"],
                "repetition": run["repetition"],
                "host_probe_state": host_probe.get("state"),
                "toolrush_pin": (host_probe.get("pins") or {}).get("toolrush"),
                "preflight": preflight,
                "preflight_snapshot": snapshot,
                "fallback_used": False,
            }
            run_id = f"{pair_id}--{int(run['sequence']):03d}--{condition}"
            evidence_path = write_run_evidence(
                session / "runs",
                run_id,
                {
                    "metadata": metadata,
                    "metrics": metrics,
                    "verifier": verifier,
                    "stdout": "",
                    "stderr": result["stderr"],
                },
            )
            run_summaries.append(
                {
                    "pair_id": pair_id,
                    "sequence": run["sequence"],
                    "condition": condition,
                    "operation": run["operation"],
                    "sample_kind": run["sample_kind"],
                    "repetition": run["repetition"],
                    "verifier": verifier,
                    "metrics": metrics,
                    "evidence_path": str(evidence_path),
                }
            )

    if excluded_pair_ids and correctness_failures:
        state = "COMPLETE_WITH_EXCLUSIONS_AND_CORRECTNESS_FAILURES"
    elif excluded_pair_ids:
        state = "COMPLETE_WITH_EXCLUSIONS"
    elif correctness_failures:
        state = "COMPLETE_WITH_CORRECTNESS_FAILURES"
    else:
        state = "COMPLETE"

    summary = {
        "experiment_id": "JAR-EXP-0013",
        "phase": "TOOL_MICROBENCH",
        "execution_id": str(execution_id),
        "state": state,
        "workload_id": plan.get("workload_id"),
        "planned_pairs": len(pairs),
        "clean_pairs": clean_pairs,
        "contaminated_pairs": len(excluded_pair_ids),
        "excluded_pair_ids": excluded_pair_ids,
        "planned_runs": len(plan["runs"]),
        "completed_runs": len(run_summaries),
        "correctness_failures": correctness_failures,
        "performance_evidence": True,
        "runs": run_summaries,
    }
    _write_json_exclusive(session / "summary.json", summary)
    return summary


def load_tool_microbench_workload(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return _require_mapping(payload, "tool microbenchmark workload")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Freeze the JAR-EXP-0013 Phase-2 A/B tool microbenchmark plan."
    )
    parser.add_argument("--workload", required=True, help="Frozen tool_microbench.yaml")
    parser.add_argument("--protocol", required=True, help="Frozen protocol.yaml")
    parser.add_argument("--output", required=True, help="Exclusive output plan JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    workload = load_tool_microbench_workload(Path(args.workload))
    protocol = load_protocol(Path(args.protocol))
    plan = build_tool_microbench_plan(workload, protocol)
    write_tool_microbench_plan(Path(args.output), plan)
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
