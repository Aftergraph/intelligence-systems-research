from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


class JevError(RuntimeError):
    """Raised when the TypeSafe Jev Decision API cannot produce a valid response."""


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class ChoiceAnswer:
    choice: str
    confidence: float = 0.0
    probabilities: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoreAnswer:
    score: float
    confidence: float = 0.0
    probabilities: dict[str, float] = field(default_factory=dict)
    legend: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NoulAnswer:
    noul: float
    confidence: float = 0.0


@dataclass
class SystemOneResponse:
    model: str
    answers: dict[str, dict[str, Any]]
    usage: Usage = field(default_factory=Usage)
    raw: dict[str, Any] = field(default_factory=dict)
    request_ids: tuple[str, ...] = ()

    def choice(self, key: str) -> ChoiceAnswer:
        a = self.answers[key]
        return ChoiceAnswer(
            choice=str(a["choice"]),
            confidence=float(a.get("confidence", 0.0) or 0.0),
            probabilities={str(k): float(v) for k, v in (a.get("probabilities") or {}).items()},
        )

    def score(self, key: str) -> ScoreAnswer:
        a = self.answers[key]
        return ScoreAnswer(
            score=float(a["score"]),
            confidence=float(a.get("confidence", 0.0) or 0.0),
            probabilities={str(k): float(v) for k, v in (a.get("probabilities") or {}).items()},
            legend=dict(a.get("legend") or {}),
        )

    def noul(self, key: str) -> float:
        a = self.answers[key]
        value = a.get("noul", a.get("probability", a.get("value")))
        if value is None:
            raise JevError(f"Answer {key!r} has no noul/probability/value field")
        return float(value)


class JevClient:
    """Small dependency-free client for TypeSafe's Jev System One API.

    The official API documents POST /v1/systemone with typed `choice`, `score`,
    and `noul` questions plus GET /v1/models. This client intentionally keeps the
    wire contract explicit rather than hiding it behind an LLM SDK.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.typesafe.ai",
        model: str = "jev-latest",
        timeout: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("TypeSafe API key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.Client(
            timeout=timeout,
            transport=transport,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "aftergraph-jev-engineering/1.6",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "JevClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def models(self) -> list[dict[str, Any]]:
        response = self._client.get(f"{self.base_url}/v1/models")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise JevError(f"Jev models request failed: HTTP {response.status_code}: {response.text[:500]}") from exc
        payload = response.json()
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("models", "data", "items"):
                if isinstance(payload.get(key), list):
                    return list(payload[key])
        raise JevError("Unexpected GET /v1/models response shape")

    def system_one(
        self,
        *,
        state: Any,
        questions: dict[str, dict[str, Any]],
        model: str | None = None,
    ) -> SystemOneResponse:
        body = {
            "model": model or self.model,
            "state": state,
            "questions": questions,
        }
        response = self._client.post(f"{self.base_url}/v1/systemone", json=body)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise JevError(
                f"Jev System One request failed: HTTP {response.status_code}: {response.text[:1000]}"
            ) from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise JevError("Jev returned non-JSON response") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("answers"), dict):
            raise JevError("Jev response is missing typed `answers`")
        usage_payload = payload.get("usage") or {}
        usage = Usage(
            input_tokens=int(usage_payload.get("input_tokens", 0) or 0),
            output_tokens=int(usage_payload.get("output_tokens", 0) or 0),
        )
        request_ids = []
        for header in ("x-typesafe-request-id", "x-request-id", "x-trace-id", "request-id"):
            value = response.headers.get(header)
            if value and value not in request_ids:
                request_ids.append(value)
        payload_id = payload.get("id")
        if payload_id and str(payload_id) not in request_ids:
            request_ids.append(str(payload_id))
        return SystemOneResponse(
            model=str(payload.get("model", model or self.model)),
            answers=dict(payload["answers"]),
            usage=usage,
            raw=payload,
            request_ids=tuple(request_ids),
        )