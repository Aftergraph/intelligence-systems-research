from __future__ import annotations

from time import perf_counter_ns


def replay_trace(steps: list[dict], adapter) -> list[dict]:
    """Replay an ordered trace and return only observable adapter results."""
    return [adapter.execute(step["operation"], step.get("payload", {})) for step in steps]


def replay_trace_timed(steps: list[dict], adapter) -> list[dict]:
    """Replay a trace while retaining per-step monotonic wall timings."""
    results = []
    for step in steps:
        started = perf_counter_ns()
        observable = adapter.execute(step["operation"], step.get("payload", {}))
        elapsed_ms = (perf_counter_ns() - started) / 1_000_000
        results.append({"operation": step["operation"], "observable": observable, "elapsed_ms": elapsed_ms})
    return results
