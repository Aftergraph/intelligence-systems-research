from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

import httpx

from .jev_client import JevClient


@dataclass(frozen=True, slots=True)
class ProviderCheck:
    provider: str
    check: str
    ok: bool
    latency_ms: float
    detail: str

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "check": self.check,
            "ok": self.ok,
            "latency_ms": round(self.latency_ms, 2),
            "detail": self.detail,
        }


def _safe_detail(text: str, secrets: tuple[str, ...]) -> str:
    out = text
    for secret in secrets:
        if secret:
            out = out.replace(secret, "[REDACTED]")
    return out[:500]


def _elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000.0


def check_typesafe(*, api_key: str, base_url: str = "https://api.typesafe.ai", model: str = "jev-latest", transport: httpx.BaseTransport | None = None) -> list[ProviderCheck]:
    results: list[ProviderCheck] = []
    start = time.perf_counter()
    try:
        with JevClient(api_key=api_key, base_url=base_url, model=model, timeout=20.0, transport=transport) as client:
            models = client.models()
        results.append(ProviderCheck("typesafe", "models", True, _elapsed_ms(start), f"models={len(models)}"))
    except Exception as exc:  # provider boundary; result must remain structured
        results.append(ProviderCheck("typesafe", "models", False, _elapsed_ms(start), _safe_detail(f"{type(exc).__name__}: {exc}", (api_key,))))
        return results

    start = time.perf_counter()
    try:
        with JevClient(api_key=api_key, base_url=base_url, model=model, timeout=20.0, transport=transport) as client:
            response = client.system_one(
                state={"task": "provider smoke check", "risk": "none"},
                questions={"continue": {"type": "noul", "true": "continue", "false": "stop"}},
            )
        response.noul("continue")
        results.append(ProviderCheck("typesafe", "system_one", True, _elapsed_ms(start), f"model={response.model}"))
    except Exception as exc:
        results.append(ProviderCheck("typesafe", "system_one", False, _elapsed_ms(start), _safe_detail(f"{type(exc).__name__}: {exc}", (api_key,))))
    return results


def check_dialagram(*, api_key: str, base_url: str = "https://dialagram.me/router/v1", model: str = "qwen-3.8-max-thinking", transport: httpx.BaseTransport | None = None) -> list[ProviderCheck]:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "User-Agent": "aftergraph-jev-engineering/1.6"}
    with httpx.Client(timeout=30.0, transport=transport, headers=headers) as client:
        start = time.perf_counter()
        try:
            response = client.get(f"{base_url.rstrip('/')}/models")
            response.raise_for_status()
            payload: Any = response.json()
            models = payload.get("data", []) if isinstance(payload, dict) else []
            results = [ProviderCheck("dialagram", "models", True, _elapsed_ms(start), f"models={len(models)}")]
        except Exception as exc:
            return [ProviderCheck("dialagram", "models", False, _elapsed_ms(start), _safe_detail(f"{type(exc).__name__}: {exc}", (api_key,)))]

        start = time.perf_counter()
        try:
            response = client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
                    "max_tokens": 8,
                    "temperature": 0,
                },
            )
            response.raise_for_status()
            payload = response.json()
            choices = payload.get("choices", []) if isinstance(payload, dict) else []
            if not choices:
                raise RuntimeError("response has no choices")
            results.append(ProviderCheck("dialagram", "chat_completions", True, _elapsed_ms(start), f"model={payload.get('model', model)}"))
        except Exception as exc:
            results.append(ProviderCheck("dialagram", "chat_completions", False, _elapsed_ms(start), _safe_detail(f"{type(exc).__name__}: {exc}", (api_key,))))
        return results


def run_provider_smoke(*, typesafe_api_key: str, dialagram_api_key: str, typesafe_base_url: str = "https://api.typesafe.ai", dialagram_base_url: str = "https://dialagram.me/router/v1", dialagram_model: str = "qwen-3.8-max-thinking") -> dict[str, object]:
    checks = [
        *check_typesafe(api_key=typesafe_api_key, base_url=typesafe_base_url),
        *check_dialagram(api_key=dialagram_api_key, base_url=dialagram_base_url, model=dialagram_model),
    ]
    return {
        "ok": bool(checks) and all(check.ok for check in checks),
        "checks": [check.to_dict() for check in checks],
    }
