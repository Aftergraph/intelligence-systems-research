from __future__ import annotations

from math import ceil
from statistics import median
from time import perf_counter_ns


def _elapsed_ms(callable_):
    started = perf_counter_ns()
    observable = callable_()
    return (perf_counter_ns() - started) / 1_000_000, observable


def summarize_samples(samples_ms: list[float]) -> dict:
    if not samples_ms:
        raise ValueError("samples_ms must not be empty")
    raw = [float(value) for value in samples_ms]
    ordered = sorted(raw)
    rank = max(1, ceil(0.95 * len(ordered))) - 1
    return {
        "samples_ms": raw,
        "median_ms": median(raw),
        "p95_ms": ordered[rank],
        "min_ms": min(raw),
        "max_ms": max(raw),
    }


def run_microbenchmark(adapter, operation: str, payload: dict, *, warm_repetitions: int = 20, include_cold: bool = True) -> dict:
    if warm_repetitions < 1:
        raise ValueError("warm_repetitions must be >= 1")
    cold_ms = None
    cold_observable = None
    if include_cold:
        cold_ms, cold_observable = _elapsed_ms(lambda: adapter.execute(operation, payload))
    warm_samples = []
    last_observable = None
    for _ in range(warm_repetitions):
        elapsed_ms, last_observable = _elapsed_ms(lambda: adapter.execute(operation, payload))
        warm_samples.append(elapsed_ms)
    return {
        "operation": operation,
        "cold_ms": cold_ms,
        "cold_observable": cold_observable,
        "warm": summarize_samples(warm_samples),
        "last_observable": last_observable,
    }
