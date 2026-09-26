from __future__ import annotations

import pytest

from jev_engineering.provider_failover import (
    FailureKind,
    ProviderFailure,
    ProviderFailoverRouter,
    ProviderRoute,
)


def test_failover_stays_on_same_logical_model_by_default() -> None:
    routes = [
        ProviderRoute("dialagram-qwen", "dialagram", "qwen-3.8-max-thinking", "qwen-frontier", priority=10),
        ProviderRoute("openrouter-qwen", "openrouter", "qwen/qwen-3.8-max-thinking", "qwen-frontier", priority=20),
        ProviderRoute("openai-sol", "openai", "gpt-5.6-sol", "sol-frontier", priority=30),
    ]
    router = ProviderFailoverRouter(routes)
    called = []
    def op(route: ProviderRoute):
        called.append(route.route_id)
        if route.route_id == "dialagram-qwen":
            raise ProviderFailure(FailureKind.TRANSIENT, "timeout")
        return "ok"
    result = router.execute(op, logical_model="qwen-frontier")
    assert result.value == "ok"
    assert result.route.route_id == "openrouter-qwen"
    assert called == ["dialagram-qwen", "openrouter-qwen"]
    assert "openai-sol" not in called


def test_auth_failure_does_not_silently_fail_over_unless_policy_allows_it() -> None:
    router = ProviderFailoverRouter([
        ProviderRoute("a", "p1", "m", "logical", priority=1),
        ProviderRoute("b", "p2", "m", "logical", priority=2),
    ])
    def op(route: ProviderRoute):
        raise ProviderFailure(FailureKind.AUTH, "bad key")
    with pytest.raises(ProviderFailure, match="bad key"):
        router.execute(op, logical_model="logical")


def test_cross_model_fallback_requires_explicit_opt_in() -> None:
    router = ProviderFailoverRouter([
        ProviderRoute("q", "p", "q", "qwen", priority=1),
        ProviderRoute("s", "p", "s", "sol", priority=2),
    ])
    with pytest.raises(RuntimeError, match="eligible provider routes"):
        router.execute(lambda r: "ok", logical_model="missing")
    result = router.execute(lambda r: "ok", logical_model="missing", allow_cross_model=True)
    assert result.route.route_id == "q"
