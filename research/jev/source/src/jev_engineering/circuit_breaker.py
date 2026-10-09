from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import time
from typing import Callable


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(slots=True)
class _Circuit:
    consecutive_failures: int = 0
    opened_at: float | None = None
    probe_in_flight: bool = False


class CircuitBreakerRegistry:
    def __init__(self, *, failure_threshold: int = 3, recovery_seconds: float = 30.0, clock: Callable[[], float] = time.monotonic) -> None:
        if failure_threshold < 1 or recovery_seconds <= 0:
            raise ValueError("invalid circuit breaker configuration")
        self.failure_threshold = failure_threshold
        self.recovery_seconds = float(recovery_seconds)
        self.clock = clock
        self._circuits: dict[str, _Circuit] = {}

    def _get(self, route_id: str) -> _Circuit:
        return self._circuits.setdefault(route_id, _Circuit())

    def state(self, route_id: str) -> CircuitState:
        c = self._get(route_id)
        if c.opened_at is None:
            return CircuitState.CLOSED
        if self.clock() - c.opened_at >= self.recovery_seconds:
            return CircuitState.HALF_OPEN
        return CircuitState.OPEN

    def allow(self, route_id: str) -> bool:
        state = self.state(route_id)
        c = self._get(route_id)
        if state is CircuitState.CLOSED:
            return True
        if state is CircuitState.OPEN:
            return False
        if c.probe_in_flight:
            return False
        c.probe_in_flight = True
        return True

    def record_success(self, route_id: str) -> None:
        c = self._get(route_id)
        c.consecutive_failures = 0
        c.opened_at = None
        c.probe_in_flight = False

    def record_failure(self, route_id: str) -> None:
        c = self._get(route_id)
        c.probe_in_flight = False
        c.consecutive_failures += 1
        if c.consecutive_failures >= self.failure_threshold:
            c.opened_at = self.clock()
