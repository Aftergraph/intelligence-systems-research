from __future__ import annotations

import json
from typing import Any

import httpx

from .jev_client import SystemOneResponse, Usage
from .openai_decisions import OpenAIDecisionBackend, OpenAIDecisionError


class OpenAICompatibleDecisionBackend(OpenAIDecisionBackend):
    """Typed Choice/Score/Noul decisions over an OpenAI-compatible chat endpoint.

    This adapter exists for gateways such as Dialagram/Nexum that expose
    `/chat/completions` rather than OpenAI's Responses API. The backend still
    fails closed: every requested key must be returned through the forced
    `submit_decisions` tool and all values are validated locally.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout: float = 120.0,
        transport: httpx.BaseTransport | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI-compatible API key is required")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.reasoning_effort = None
        self.extra = dict(extra or {})
        self._client = httpx.Client(
            timeout=timeout,
            transport=transport,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "aftergraph-jev-engineering/1.6",
            },
        )

    def system_one(
        self,
        *,
        state: Any,
        questions: dict[str, dict[str, Any]],
        model: str | None = None,
    ) -> SystemOneResponse:
        if not questions:
            raise OpenAIDecisionError("At least one typed question is required")
        chosen_model = model or self.model
        parameters = self._parameters_schema(questions)
        body: dict[str, Any] = {
            "model": chosen_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the typed decision plane for a governed coding system. "
                        "Answer every requested Choice, Score, or Noul exactly once. "
                        "Use the supplied state only. Calibrate probabilities conservatively. "
                        "Do not propose code or actions; submit only the typed decisions."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"state": state, "questions": questions},
                        ensure_ascii=False,
                        separators=(",", ":"),
                        default=str,
                    ),
                },
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "submit_decisions",
                        "description": "Submit all requested typed decisions.",
                        "parameters": parameters,
                    },
                }
            ],
            "tool_choice": {
                "type": "function",
                "function": {"name": "submit_decisions"},
            },
        }
        body.update(self.extra)
        response = self._client.post(f"{self.base_url}/chat/completions", json=body)
        try:
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OpenAIDecisionError(f"Compatible decision request failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise OpenAIDecisionError("Compatible provider returned a non-object response")

        choices = payload.get("choices") or []
        message = choices[0].get("message") if choices and isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            raise OpenAIDecisionError("Compatible provider returned no assistant message")
        selected_call: dict[str, Any] | None = None
        for item in message.get("tool_calls") or []:
            if not isinstance(item, dict):
                continue
            function = item.get("function") or {}
            if isinstance(function, dict) and function.get("name") == "submit_decisions":
                selected_call = function
                break
        if selected_call is None:
            raise OpenAIDecisionError("Compatible provider did not call submit_decisions")

        raw_arguments = selected_call.get("arguments") or "{}"
        try:
            arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
        except json.JSONDecodeError as exc:
            raise OpenAIDecisionError("submit_decisions emitted invalid JSON") from exc
        if not isinstance(arguments, dict) or not isinstance(arguments.get("answers"), dict):
            raise OpenAIDecisionError("submit_decisions is missing answers")
        answers = self._validate_answers(questions, dict(arguments["answers"]))

        usage_payload = payload.get("usage") or {}
        usage = Usage(
            input_tokens=int(
                usage_payload.get("prompt_tokens", usage_payload.get("input_tokens", 0)) or 0
            ),
            output_tokens=int(
                usage_payload.get("completion_tokens", usage_payload.get("output_tokens", 0)) or 0
            ),
        )
        request_ids: list[str] = []
        for header in ("x-request-id", "x-trace-id", "request-id"):
            value = response.headers.get(header)
            if value and value not in request_ids:
                request_ids.append(value)
        payload_id = payload.get("id")
        if payload_id and str(payload_id) not in request_ids:
            request_ids.append(str(payload_id))
        return SystemOneResponse(
            model=str(payload.get("model") or chosen_model),
            answers=answers,
            usage=usage,
            raw=payload,
            request_ids=tuple(request_ids),
        )