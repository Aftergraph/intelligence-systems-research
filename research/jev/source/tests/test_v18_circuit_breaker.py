from __future__ import annotations

import pytest

from jev_engineering.circuit_breaker import CircuitBreakerRegistry, CircuitState
from jev_engineering.provider_failover import FailureKind, ProviderFailure, ProviderFailoverRouter, ProviderRoute


def test_circuit_breaker_opens_provider_route_and_router_skips_it() -> None:
    clock = [100.0]
    breakers = CircuitBreakerRegistry(failure_threshold=2, recovery_seconds=30, clock=lambda: clock[0])
    router = ProviderFailoverRouter([
        ProviderRoute("a", "p1", "m", "logical", priority=1),
        ProviderRoute("b", "p2", "m", "logical", priority=2),
    ], circuit_breakers=breakers)
    def fail_a(route):
        if route.route_id == "a":
            raise ProviderFailure(FailureKind.TRANSIENT, "down")
        return "ok"
    assert router.execute(fail_a, logical_model="logical").route.route_id == "b"
    assert router.execute(fail_a, logical_model="logical").route.route_id == "b"
    assert breakers.state("a") is CircuitState.OPEN
    called=[]
    result=router.execute(lambda r: called.append(r.route_id) or "ok", logical_model="logical")
    assert result.route.route_id == "b"
    assert called == ["b"]
    clock[0] += 31
    assert breakers.state("a") is CircuitState.HALF_OPEN
