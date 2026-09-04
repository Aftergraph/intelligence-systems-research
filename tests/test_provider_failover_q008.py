"""
test_provider_failover_q008.py
==============================

Pins Q-008 (provider independence): the rate-limit / circuit-breaker
module is in place; this test simulates multi-provider failover and
verifies the basic behaviors.

We test in-process only (the multi-host coordination is a known
ceiling, documented in the rate_limit module).
"""

import os
import sys
import time
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)
sys.path.insert(0, str(Path(workspace) / "experiments" / "live_benchmark"))

import study011_rate_limit as rl


@pytest.fixture(autouse=True)
def reset():
    """Reset the global breaker/limiter registry between tests."""
    rl.reset_all()
    yield
    rl.reset_all()


def test_circuit_breaker_opens_after_threshold_failures():
    """The circuit breaker must open after the threshold number of
    consecutive failures, preventing further requests from
    saturating a failing provider."""
    cb = rl.CircuitBreaker(provider="dialagram", model="qwen", threshold=3, cooldown_seconds=10.0)
    # 2 failures: still closed
    cb.record_failure()
    cb.record_failure()
    allow, reason = cb.allow()
    assert allow, f"Circuit opened too early (after 2 failures): {reason}"
    # 3rd failure: opens
    cb.record_failure()
    allow, reason = cb.allow()
    assert not allow, (
        f"Circuit did not open after 3 failures. reason={reason}"
    )


def test_circuit_breaker_resets_on_success():
    """A success after a few failures must reset the failure count
    (not trip the breaker)."""
    cb = rl.CircuitBreaker(provider="dialagram", model="qwen", threshold=3, cooldown_seconds=10.0)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()  # reset
    cb.record_failure()
    cb.record_failure()
    # Still under threshold (count was reset)
    allow, reason = cb.allow()
    assert allow, f"Circuit opened after success-reset: {reason}"


def test_circuit_breaker_cooldown():
    """After the cooldown period, the circuit must transition to
    half-open and allow a probe request."""
    cb = rl.CircuitBreaker(provider="dialagram", model="qwen", threshold=2, cooldown_seconds=0.1)
    cb.record_failure()
    cb.record_failure()
    allow, _ = cb.allow()
    assert not allow
    # Wait for cooldown
    time.sleep(0.15)
    allow, reason = cb.allow()
    assert allow, (
        f"Circuit did not allow probe after cooldown: {reason}"
    )


def test_rate_limiter_pacing():
    """The rate limiter must enforce a minimum interval between
    requests (pacing)."""
    rl1 = rl.RateLimiter(provider="dialagram", model="qwen", min_spacing_seconds=0.2, burst=1)
    # First request: no wait
    wait = rl1.wait_time()
    assert wait == 0.0 or wait < 0.1, f"First request should not wait: {wait}"
    rl1.acquire()
    # Second request immediately: must wait ~0.2s
    wait = rl1.wait_time()
    assert 0.15 <= wait <= 0.3, (
        f"Second request wait_time={wait} not in [0.15, 0.3]s"
    )


def test_rate_limiter_retry_after_override():
    """When a 429 response is received with a Retry-After header,
    the limiter must use the server's hint, not the default pacing."""
    rl2 = rl.RateLimiter(provider="dialagram", model="qwen", min_spacing_seconds=1.0, burst=1)
    rl2.register_retry_after(5.0)
    wait = rl2.wait_time()
    assert wait >= 4.5, (
        f"Retry-After not honored: wait_time={wait}s (expected >= 4.5s)"
    )


def test_checkpoint_dedup():
    """The checkpoint must deduplicate run_ids so a retried run
    doesn't produce double side effects."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        cp = rl.CheckpointState(path=Path(tmp) / "ckpt.jsonl")
        assert not cp.has_run("run-1")
        cp.record(run_id="run-1", workload_id="W-1", condition="A", provider="dialagram", model="qwen", replicate_id=1)
        assert cp.has_run("run-1")
        # Recording again is idempotent (no double side effect)
        cp.record(run_id="run-1", workload_id="W-1", condition="A", provider="dialagram", model="qwen", replicate_id=1)
        assert len(cp.completed_keys()) == 1


def test_provider_isolation():
    """Circuit breakers for different providers must be independent.
    A failure on Dialagram must not open the OpenRouter breaker."""
    rl.reset_all()
    cb_d = rl.get_breaker("dialagram", "qwen-3.8-max", threshold=2)
    cb_o = rl.get_breaker("openrouter", "gemma-4-31b", threshold=2)
    # Trip Dialagram
    cb_d.record_failure()
    cb_d.record_failure()
    # OpenRouter should still be closed
    allow, _ = cb_o.allow()
    assert allow, "OpenRouter breaker opened because Dialagram was tripped"


def test_failover_pattern():
    """Simulated failover: when the primary provider's circuit is
    open, requests should be attempted on the secondary provider."""
    rl.reset_all()
    # Simulate primary failing
    primary = rl.get_breaker("dialagram", "qwen", threshold=2)
    primary.record_failure()
    primary.record_failure()
    allow, _ = primary.allow()
    assert not allow, "Primary should be open after 2 failures"
    # Fallback: secondary is still available
    secondary = rl.get_breaker("openrouter", "gemma", threshold=2)
    allow, reason = secondary.allow()
    assert allow, f"Fallback provider unavailable: {reason}"
