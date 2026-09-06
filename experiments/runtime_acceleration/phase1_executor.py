from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter_ns
from typing import Callable

from .evidence import write_run_evidence
from .host_preflight import check_preflight
from .runners.trace_replay import replay_trace_timed
from .verification.differential import compare_observable

_EXPECTED_CONDITIONS = ("A", "B", "C", "D")


def _write_json_exclusive(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _validate_inputs(plan: dict, protocol: dict, host_probe: dict) -> list[tuple[str, list[dict]]]:
    if host_probe.get("experiment_id") != "JAR-EXP-0013" or host_probe.get("state") != "READY":
        raise ValueError("Phase-1 execution requires a JAR-EXP-0013 controlled host in READY state")
    if plan.get("experiment_id") != "JAR-EXP-0013" or protocol.get("experiment_id") != "JAR-EXP-0013":
        raise ValueError("unexpected experiment identity")
    if plan.get("phase") != "TRACE_REPLAY" or plan.get("plan_only") is not True:
        raise ValueError("Phase-1 requires the frozen TRACE_REPLAY measurement plan")
    if tuple(plan.get("conditions", ())) != _EXPECTED_CONDITIONS:
        raise ValueError("measurement plan conditions must be exactly A/B/C/D")
    if set((protocol.get("conditions") or {}).keys()) != set(_EXPECTED_CONDITIONS):
        raise ValueError("protocol conditions must be exactly A/B/C/D")

    trace = plan.get("trace")
    if not isinstance(trace, dict) or not isinstance(trace.get("steps"), list) or not trace["steps"]:
        raise ValueError("measurement plan trace is missing steps")

    runs = plan.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("measurement plan has no runs")
    expected_sequences = list(range(1, len(runs) + 1))
    if [run.get("sequence") for run in runs] != expected_sequences:
        raise ValueError("measurement plan sequence must be contiguous and frozen")

    grouped: dict[str, list[dict]] = {}
    for run in runs:
        pair_id = run.get("pair_id")
        condition = run.get("condition")
        if not isinstance(pair_id, str) or not pair_id:
            raise ValueError("every run requires a pair_id")
        if condition not in _EXPECTED_CONDITIONS:
            raise ValueError(f"invalid condition: {condition}")
        grouped.setdefault(pair_id, []).append(dict(run))

    pairs = list(grouped.items())
    for pair_id, pair_runs in pairs:
        conditions = [run["condition"] for run in pair_runs]
        if len(pair_runs) != 4 or set(conditions) != set(_EXPECTED_CONDITIONS):
            raise ValueError(f"paired block {pair_id} must contain A/B/C/D exactly once")

    repetitions = plan.get("repetitions")
    if repetitions != len(pairs):
        raise ValueError("measurement plan repetitions do not match paired blocks")
    return pairs


def _measure_trace(steps: list[dict], adapter) -> dict:
    started = perf_counter_ns()
    timed_steps = replay_trace_timed(steps, adapter)
    wall_ms = (perf_counter_ns() - started) / 1_000_000
    browser_ms = sum(
        float(step["elapsed_ms"])
        for step in timed_steps
        if str(step["operation"]).startswith("browser_")
    )
    tool_ms = sum(
        float(step["elapsed_ms"])
        for step in timed_steps
        if not str(step["operation"]).startswith("browser_")
    )
    return {
        "trace_wall_clock_ms": wall_ms,
        "tool_time_total_ms": tool_ms,
        "browser_time_total_ms": browser_ms,
        "steps": timed_steps,
        "observables": [step["observable"] for step in timed_steps],
    }


def _failed_execution(exc: Exception, *, prior_error: str | None = None) -> dict:
    error = f"{type(exc).__name__}: {exc}"
    if prior_error:
        error = f"{prior_error}; cleanup {error}"
    return {
        "trace_wall_clock_ms": None,
        "tool_time_total_ms": None,
        "browser_time_total_ms": None,
        "steps": [],
        "observables": [],
        "error": error,
    }


def _verifier_for(condition: str, execution: dict, control: dict | None) -> dict:
    if execution.get("error") is not None:
        return {
            "verified": False,
            "classification": "EXECUTION_ERROR",
            "details": {"error": execution["error"]},
            "observables": [],
        }
    observables = execution["observables"]
    if condition == "A":
        return {
            "verified": True,
            "classification": "CONTROL_REFERENCE",
            "details": {},
            "observables": observables,
        }
    if control is None or control.get("error") is not None:
        return {
            "verified": False,
            "classification": "CONTROL_UNAVAILABLE",
            "details": {},
            "observables": observables,
        }
    differential = compare_observable(control["observables"], observables)
    return {
        "verified": differential.equal,
        "classification": differential.classification,
        "details": differential.details,
        "observables": observables,
    }


def execute_phase1_plan(
    plan: dict,
    protocol: dict,
    host_probe: dict,
    *,
    evidence_root: str | Path,
    execution_id: str,
    adapter_factory: Callable[[str], object],
    snapshot_provider: Callable[[], dict],
) -> dict:
    """Execute frozen Phase-1 A/B/C/D trace blocks on an already READY controlled host.

    The caller supplies the real host treatment factory. This function never substitutes a
    fallback implementation. Every block is preflight-gated before any treatment is invoked,
    and all run evidence is written append-only under one immutable execution id.
    """
    pairs = _validate_inputs(plan, protocol, host_probe)

    root = Path(evidence_root)
    root.mkdir(parents=True, exist_ok=True)
    session = root / execution_id
    session.mkdir(parents=False, exist_ok=False)
    (session / "runs").mkdir()
    (session / "blocks").mkdir()

    trace = plan["trace"]
    steps = [dict(step) for step in trace["steps"]]
    limits = dict(protocol["preflight"])
    run_summaries: list[dict] = []
    excluded_pair_ids: list[str] = []
    clean_pairs = 0
    correctness_failures = 0

    for pair_id, pair_runs in pairs:
        snapshot = dict(snapshot_provider())
        preflight = check_preflight(snapshot, limits)
        block_state = "CLEAN" if preflight["clean"] else "CONTAMINATED"
        _write_json_exclusive(
            session / "blocks" / f"{pair_id}.json",
            {
                "experiment_id": "JAR-EXP-0013",
                "phase": "TRACE_REPLAY",
                "pair_id": pair_id,
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
            condition = run["condition"]
            adapter = None
            try:
                adapter = adapter_factory(condition)
                execution = _measure_trace(steps, adapter)
                execution["error"] = None
            except Exception as exc:  # Fail closed: record the treatment failure, never fallback.
                execution = _failed_execution(exc)
            finally:
                if adapter is not None:
                    try:
                        close = getattr(adapter, "close")
                        close()
                    except Exception as close_exc:
                        execution = _failed_execution(
                            close_exc,
                            prior_error=execution.get("error"),
                        )
            executed.append((run, execution))

        control_execution = next(
            (execution for run, execution in executed if run["condition"] == "A"),
            None,
        )

        for run, execution in executed:
            condition = run["condition"]
            verifier = _verifier_for(condition, execution, control_execution)
            if condition != "A" and verifier["verified"] is not True:
                correctness_failures += 1

            metrics = {
                "trace_wall_clock_ms": execution["trace_wall_clock_ms"],
                "tool_time_total_ms": execution["tool_time_total_ms"],
                "browser_time_total_ms": execution["browser_time_total_ms"],
                "step_timings": [
                    {"operation": step["operation"], "elapsed_ms": step["elapsed_ms"]}
                    for step in execution["steps"]
                ],
            }
            metadata = {
                "experiment_id": "JAR-EXP-0013",
                "protocol_revision": protocol.get("revision"),
                "phase": "TRACE_REPLAY",
                "execution_id": execution_id,
                "pair_id": pair_id,
                "sequence": run["sequence"],
                "condition": condition,
                "trace_id": run.get("trace_id"),
                "trace_revision": run.get("trace_revision"),
                "host_probe_state": host_probe.get("state"),
                "host_pins": dict(host_probe.get("pins") or {}),
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
                    "stderr": execution.get("error") or "",
                },
            )
            run_summaries.append(
                {
                    "pair_id": pair_id,
                    "sequence": run["sequence"],
                    "condition": condition,
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
        "phase": "TRACE_REPLAY",
        "execution_id": execution_id,
        "state": state,
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
