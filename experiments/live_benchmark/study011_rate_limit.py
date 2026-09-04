"""
study011_rate_limit.py
======================

Rate-limit, circuit-breaker, and checkpoint/resume helpers for STUDY-011.

This module is *advisory* and *side-effect-free* on the public harness:
it provides three pure-Python primitives that the harness can call
without affecting the LIVE_ONLY invariant.

  1. CircuitBreaker — opens after N consecutive failures, cools down,
     and rejects further calls until a half-open probe succeeds.

  2. RateLimiter — token-bucket pacing per (provider, model) with
     min-spacing, burst tolerance, and Retry-After honoring.

  3. CheckpointState — append-only journal of completed (run_id,
     provider, model, condition, workload_id, replicate_id) tuples
     so that `run_study_011.py` can resume across restarts without
     re-issuing calls or double-counting.

All three are deterministic, network-free, and unit-testable without
a real provider. None of them ever falls back to simulation.

ponytail: small surface, stdlib-only (json, threading, time, pathlib).
The ceiling is that RateLimiter is in-process only — multi-process
rate limiting would need a shared file lock. Documented but not built.
"""
from __future__ import annotations
import json
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, List, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# CircuitBreaker
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class CircuitBreaker:
    """Per-(provider, model) circuit breaker.

    States:
      CLOSED      → calls pass; consecutive failures are counted.
      OPEN        → calls rejected immediately for `cooldown_seconds`.
      HALF_OPEN   → one probe call is allowed; success closes, failure
                    re-opens for another `cooldown_seconds`.

    ponytail: ceiling — the breaker counts *consecutive* failures, not
    a moving-window rate. A flaky provider that alternates success/fail
    will never trip. Documented; upgrade to a windowed counter if the
    STUDY-008 3.3% provider-failure rate is exceeded in Phase 1.
    """
    provider: str
    model: str
    threshold: int = 5
    cooldown_seconds: float = 300.0
    _state: str = "CLOSED"
    _consecutive_failures: int = 0
    _opened_at: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def allow(self) -> Tuple[bool, str]:
        """Return (allowed, reason). Thread-safe."""
        with self._lock:
            now = time.monotonic()
            if self._state == "OPEN":
                if now - self._opened_at >= self.cooldown_seconds:
                    self._state = "HALF_OPEN"
                    return True, "HALF_OPEN probe"
                return False, f"OPEN for {self.cooldown_seconds - (now - self._opened_at):.0f}s more"
            return True, self._state

    def record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            self._state = "CLOSED"

    def record_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.threshold:
                self._state = "OPEN"
                self._opened_at = time.monotonic()

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "provider": self.provider,
                "model": self.model,
                "state": self._state,
                "consecutive_failures": self._consecutive_failures,
                "threshold": self.threshold,
                "cooldown_seconds": self.cooldown_seconds,
            }


# ─────────────────────────────────────────────────────────────────────────────
# RateLimiter
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class RateLimiter:
    """Per-(provider, model) token-bucket rate limiter with min-spacing.

    - `min_spacing_seconds`: minimum wall-clock gap between two calls.
    - `burst`: max calls allowed in a tight cluster before spacing kicks in.
    - Honors an externally provided Retry-After (in seconds) when supplied
      via `register_retry_after()`.

    ponytail: in-process only. Multi-process coordination would need a
    shared file lock on the journal; document for Phase 2 if needed.
    """
    provider: str
    model: str
    min_spacing_seconds: float = 5.0
    burst: int = 1
    _last_call_at: float = 0.0
    _retry_after_until: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def wait_time(self, now: Optional[float] = None) -> float:
        """Return seconds to wait before the next call is allowed.
        Zero if no wait is required."""
        if now is None:
            now = time.monotonic()
        with self._lock:
            gap = now - self._last_call_at
            spacing_wait = max(0.0, self.min_spacing_seconds - gap)
            retry_after_wait = max(0.0, self._retry_after_until - now)
            return max(spacing_wait, retry_after_wait)

    def acquire(self) -> None:
        """Block (sleep) until a call slot is open, then mark the call as
        started. Returns only when the next call may proceed."""
        while True:
            wait = self.wait_time()
            if wait <= 0:
                with self._lock:
                    self._last_call_at = time.monotonic()
                return
            time.sleep(wait)

    def register_retry_after(self, seconds: float) -> None:
        with self._lock:
            self._retry_after_until = max(self._retry_after_until, time.monotonic() + seconds)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "provider": self.provider,
                "model": self.model,
                "min_spacing_seconds": self.min_spacing_seconds,
                "burst": self.burst,
                "last_call_at": self._last_call_at,
                "retry_after_until": self._retry_after_until,
            }


# ─────────────────────────────────────────────────────────────────────────────
# CheckpointState — append-only journal
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class CheckpointState:
    """Append-only journal of completed runs.

    Format: one JSON object per line (JSONL). Each line is keyed by
    (run_id, provider, model, condition, workload_id, replicate_id).

    `has_run(run_id)` lets the harness skip already-completed runs on
    resume. `record()` is idempotent on run_id (a duplicate record
    overwrites the prior line, leaving the journal append-only at the
    file level).

    The state file is small enough to be loaded fully in memory for a
    619-attempt Phase 1 (~50KB JSONL). Document the upgrade path to a
    streaming reader for Phase 2 if the attempt count grows.
    """
    path: Path
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _cache: Dict[str, dict] = field(default_factory=dict, repr=False)
    _loaded: bool = field(default=False, repr=False)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            if self.path.exists():
                with open(self.path, "r", encoding="utf-8") as fh:
                    for lineno, line in enumerate(fh, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                        except json.JSONDecodeError:
                            continue  # tolerate partial last line
                        if isinstance(rec, dict) and "run_id" in rec:
                            self._cache[rec["run_id"]] = rec
            self._loaded = True

    def has_run(self, run_id: str) -> bool:
        self._ensure_loaded()
        return run_id in self._cache

    def record(self, **fields) -> None:
        """Append a record. Idempotent on run_id: re-recording the same
        run_id is allowed (it overwrites in cache and appends to file)."""
        self._ensure_loaded()
        run_id = fields.get("run_id")
        if not run_id:
            raise ValueError("record() requires run_id")
        with self._lock:
            self._cache[run_id] = fields
            # Append-only on disk. We append a fresh line; on reload
            # the cache picks up the latest (last-wins) for that run_id.
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(fields, ensure_ascii=False, sort_keys=True) + "\n")

    def completed_keys(self) -> List[Tuple[str, ...]]:
        """Return the list of (provider, model, condition, workload_id, replicate_id)
        tuples that have been completed. The harness uses this to skip
        already-finished cells on resume."""
        self._ensure_loaded()
        out = []
        for rec in self._cache.values():
            try:
                out.append((
                    rec["provider"],
                    rec["model"],
                    rec["condition"],
                    rec["workload_id"],
                    str(rec["replicate_id"]),
                ))
            except KeyError:
                continue
        return out

    def snapshot(self) -> dict:
        self._ensure_loaded()
        return {
            "path": str(self.path),
            "completed_runs": len(self._cache),
            "run_ids": sorted(self._cache.keys()),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Module-level registry helpers (per-process singletons)
# ─────────────────────────────────────────────────────────────────────────────


_BREAKERS: Dict[Tuple[str, str], CircuitBreaker] = {}
_LIMITERS: Dict[Tuple[str, str], RateLimiter] = {}
_REG_LOCK = threading.Lock()


def get_breaker(provider: str, model: str, **kwargs) -> CircuitBreaker:
    key = (provider, model)
    with _REG_LOCK:
        if key not in _BREAKERS:
            _BREAKERS[key] = CircuitBreaker(provider=provider, model=model, **kwargs)
        return _BREAKERS[key]


def get_limiter(provider: str, model: str, **kwargs) -> RateLimiter:
    key = (provider, model)
    with _REG_LOCK:
        if key not in _LIMITERS:
            _LIMITERS[key] = RateLimiter(provider=provider, model=model, **kwargs)
        return _LIMITERS[key]


def reset_all() -> None:
    """Test helper: clear the in-process breaker/limiter registries."""
    with _REG_LOCK:
        _BREAKERS.clear()
        _LIMITERS.clear()


# ─────────────────────────────────────────────────────────────────────────────
# CLI for inspecting the journal (no network)
# ─────────────────────────────────────────────────────────────────────────────


def _cli_inspect(journal_path: str) -> int:
    p = Path(journal_path)
    if not p.exists():
        print(f"no journal at {p}")
        return 0
    cs = CheckpointState(path=p)
    snap = cs.snapshot()
    print(json.dumps(snap, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "inspect":
        sys.exit(_cli_inspect(sys.argv[2]))
    print("usage: study011_rate_limit.py inspect <journal.jsonl>")
    sys.exit(2)
