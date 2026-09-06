import pytest

from experiments.runtime_acceleration.runners.microbench import run_microbenchmark, summarize_samples


def test_summary_retains_raw_samples_and_reports_median_p95():
    result = summarize_samples([1.0, 2.0, 3.0, 100.0])
    assert result["samples_ms"] == [1.0, 2.0, 3.0, 100.0]
    assert result["median_ms"] == 2.5
    assert result["min_ms"] == 1.0
    assert result["max_ms"] == 100.0
    assert result["p95_ms"] >= 3.0


def test_summary_rejects_empty_samples():
    with pytest.raises(ValueError):
        summarize_samples([])


class Adapter:
    def __init__(self):
        self.calls = 0

    def execute(self, operation, payload):
        self.calls += 1
        return {"operation": operation, "payload": payload}


def test_microbenchmark_keeps_one_cold_and_all_warm_samples():
    adapter = Adapter()
    result = run_microbenchmark(adapter, "read", {"path": "a.py"}, warm_repetitions=3, include_cold=True)
    assert adapter.calls == 4
    assert result["cold_ms"] >= 0
    assert len(result["warm"]["samples_ms"]) == 3
