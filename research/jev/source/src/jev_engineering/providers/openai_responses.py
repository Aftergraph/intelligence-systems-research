from __future__ import annotations

import json
from typing import Any

import httpx

from ..types import ProviderTurn, ToolCall, ToolSpec


class OpenAIResponsesError(RuntimeError):
    pass


class OpenAIResponsesSession:
    def __init__(
        self,
        *,
        client: httpx.Client,
        url: str,
        model: str,
        task: str,
        context: str,
        tools: list[ToolSpec],
        instructions: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.client = client
        self.url = url
        self.model = model
        self.tools = tools
        self.instructions = instructions
        self.extra = dict(extra or {})
        self.items: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": (
                    f"TASK\n{task}\n\nSELECTED CONTEXT\n{context}\n\n"
                    "Use tools for real repository work. The outer harness owns VERIFIED."
                ),
            }
        ]

    def _wire_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                # Optional fields in several tool schemas make strict mode invalid on some APIs.
                "strict": False,
            }
            for tool in self.tools
        ]

    def step(self, tool_results: dict[str, Any] | None = None) -> ProviderTurn:
        for call_id, value in (tool_results or {}).items():
            self.items.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(value, ensure_ascii=False, separators=(",", ":")),
                }
            )
        body: dict[str, Any] = {
            "model": self.model,
            "instructions": self.instructions,
            "input": self.items,
            "tools": self._wire_tools(),
            "tool_choice": "auto",
            "parallel_tool_calls": True,
            "store": False,
        }
        body.update(self.extra)
        response = self.client.post(self.url, json=body)
        try:
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OpenAIResponsesError(f"OpenAI Responses request failed: {exc}") from exc
        output = payload.get("output") or []
        if not isinstance(output, list):
            raise OpenAIResponsesError("Responses API returned an invalid output array")
        self.items.extend(item for item in output if isinstance(item, dict))
        calls: list[ToolCall] = []
        texts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "function_call":
                args = item.get("arguments") or "{}"
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError as exc:
                        raise OpenAIResponsesError("Model emitted invalid function-call JSON") from exc
                if not isinstance(args, dict):
                    raise OpenAIResponsesError("Function-call arguments must be a JSON object")
                calls.append(
                    ToolCall(
                        str(item.get("call_id") or item.get("id") or ""),
                        str(item.get("name") or ""),
                        dict(args),
                    )
                )
            elif item.get("type") == "message":
                for content in item.get("content") or []:
                    if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                        texts.append(str(content.get("text") or ""))
        return ProviderTurn(text="\n".join(x for x in texts if x).strip(), tool_calls=calls, raw=payload)


class OpenAIResponsesProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 120.0,
        transport: httpx.BaseTransport | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.extra = extra or {}
        self.client = httpx.Client(
            timeout=timeout,
            transport=transport,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )

    def start(self, *, task: str, context: str, tools: list[ToolSpec], instructions: str) -> OpenAIResponsesSession:
        return OpenAIResponsesSession(
            client=self.client,
            url=f"{self.base_url}/responses",
            model=self.model,
            task=task,
            context=context,
            tools=tools,
            instructions=instructions,
            extra=self.extra,
        )
