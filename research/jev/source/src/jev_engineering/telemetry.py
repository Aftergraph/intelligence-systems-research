from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


def _int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def extract_token_usage(payload: dict[str, Any] | None) -> TokenUsage:
    """Normalize token telemetry from common provider response shapes.

    Supported shapes include OpenAI Responses, OpenAI-compatible chat,
    Anthropic Messages, and Google GenerateContent. Unknown/missing usage is
    represented as zeros rather than guessed.
    """
    if not isinstance(payload, dict):
        return TokenUsage()

    google = payload.get("usageMetadata")
    if isinstance(google, dict):
        return TokenUsage(
            input_tokens=_int(google.get("promptTokenCount")),
            output_tokens=_int(google.get("candidatesTokenCount")),
            cached_input_tokens=_int(google.get("cachedContentTokenCount")),
        )

    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return TokenUsage()

    input_tokens = _int(usage.get("input_tokens", usage.get("prompt_tokens")))
    output_tokens = _int(usage.get("output_tokens", usage.get("completion_tokens")))

    cached = _int(usage.get("cache_read_input_tokens"))
    details = usage.get("input_tokens_details")
    if isinstance(details, dict):
        cached = max(cached, _int(details.get("cached_tokens")))
    prompt_details = usage.get("prompt_tokens_details")
    if isinstance(prompt_details, dict):
        cached = max(cached, _int(prompt_details.get("cached_tokens")))

    return TokenUsage(input_tokens, output_tokens, cached)


def extract_provider_request_id(payload: dict[str, Any] | None) -> str | None:
    """Extract a provider-issued response/request identifier without guessing.

    Common APIs expose ``id`` (OpenAI/Anthropic/OpenAI-compatible), while
    Google GenerateContent may expose ``responseId``. Missing identifiers remain
    missing so authenticated evidence can fail closed.
    """
    if not isinstance(payload, dict):
        return None
    for key in ("id", "responseId", "response_id", "request_id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
