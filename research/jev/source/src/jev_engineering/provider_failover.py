from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Generic, TypeVar

from .circuit_breaker import CircuitBreakerRegistry


T = TypeVar("T")


class FailureKind(str, Enum):
    TRANSIENT = "transient"
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    INVALID_REQUEST = "invalid_request"
    FATAL = "fatal"


class ProviderFailure(RuntimeError):
    def __init__(self, kind: FailureKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True, slots=True)
class ProviderRoute:
    route_id: str
    provider: str
    model: str
    logical_model: str
    priority: int = 100
    capabilities: frozenset[str] = frozenset({"text"})
    healthy: bool = True


@dataclass(frozen=True, slots=True)
class ProviderAttempt:
    route_id: str
    provider: str
    model: str
    outcome: str
    failure_kind: str | None = None


@dataclass(frozen=True, slots=True)
class FailoverResult(Generic[T]):
    value: T
    route: ProviderRoute
    attempts: tuple[ProviderAttempt, ...]


class ProviderFailoverRouter:
    """Explicit provider failover without silent logical-model substitution."""

    def __init__(self, routes: list[ProviderRoute] | tuple[ProviderRoute, ...], *, circuit_breakers: CircuitBreakerRegistry | None = None) -> None:
        if not routes:
            raise ValueError("at least one provider route is required")
        ids = [r.route_id for r in routes]
        if len(ids) != len(set(ids)):
            raise ValueError("provider route ids must be unique")
        self.routes = tuple(sorted(routes, key=lambda r: (r.priority, r.route_id)))
        self.circuit_breakers = circuit_breakers

    def eligible(
        self,
        *,
        logical_model: str,
        capability: str = "text",
        allow_cross_model: bool = False,
    ) -> tuple[ProviderRoute, ...]:
        rows = tuple(r for r in self.routes if r.healthy and capability in r.capabilities and (allow_cross_model or r.logical_model == logical_model) and (self.circuit_breakers is None or self.circuit_breakers.allow(r.route_id)))
        if not rows:
            raise RuntimeError("no eligible provider routes")
        return rows

    def execute(
        self,
        operation: Callable[[ProviderRoute], T],
        *,
        logical_model: str,
        capability: str = "text",
        allow_cross_model: bool = False,
        failover_on_auth: bool = False,
        max_attempts: int | None = None,
    ) -> FailoverResult[T]:
        routes = self.eligible(logical_model=logical_model, capability=capability, allow_cross_model=allow_cross_model)
        if max_attempts is not None:
            if max_attempts < 1:
                raise ValueError("max_attempts must be >= 1")
            routes = routes[:max_attempts]
        attempts: list[ProviderAttempt] = []
        last: ProviderFailure | None = None
        retryable = {FailureKind.TRANSIENT, FailureKind.RATE_LIMIT}
        if failover_on_auth:
            retryable.add(FailureKind.AUTH)
        for route in routes:
            try:
                value = operation(route)
            except ProviderFailure as exc:
                attempts.append(ProviderAttempt(route.route_id, route.provider, route.model, "failed", exc.kind.value))
                if self.circuit_breakers is not None and exc.kind in {FailureKind.TRANSIENT, FailureKind.RATE_LIMIT}:
                    self.circuit_breakers.record_failure(route.route_id)
                last = exc
                if exc.kind not in retryable:
                    raise
                continue
            if self.circuit_breakers is not None:
                self.circuit_breakers.record_success(route.route_id)
            attempts.append(ProviderAttempt(route.route_id, route.provider, route.model, "success"))
            return FailoverResult(value=value, route=route, attempts=tuple(attempts))
        if last is not None:
            raise last
        raise RuntimeError("provider failover exhausted")
