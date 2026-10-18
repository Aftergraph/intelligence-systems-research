from __future__ import annotations

import json
from typing import Any

import httpx

from ..types import ProviderTurn, ToolCall, ToolSpec


class AnthropicMessagesSession:
    def __init__(self, *, client: httpx.Client, url: str, model: str, task: str, context: str, tools: list[ToolSpec], instructions: str, max_tokens: int = 8192, extra: dict[str, Any] | None = None) -> None:
        self.client = client
        self.url = url
        self.model = model
        self.tools = tools
        self.instructions = instructions
        self.max_tokens = max_tokens
        self.extra = extra or {}
        self.messages: list[dict[str, Any]] = [{"role": "user", "content": f"TASK\n{task}\n\nSELECTED CONTEXT\n{context}"}]

    def step(self, tool_results: dict[str, Any] | None = None) -> ProviderTurn:
        if tool_results:
            self.messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": call_id, "content": json.dumps(result, ensure_ascii=False)}
                        for call_id, result in tool_results.items()
                    ],
                }
            )
        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": self.instructions,
            "messages": self.messages,
            "tools": [{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in self.tools],
        }
        body.update(self.extra)
        r = self.client.post(self.url, json=body)
        r.raise_for_status()
        payload = r.json()
        content = payload.get("content") or []
        self.messages.append({"role": "assistant", "content": content})
        calls: list[ToolCall] = []
        texts: list[str] = []
        for block in content:
            if block.get("type") == "tool_use":
                calls.append(ToolCall(str(block.get("id")), str(block.get("name")), dict(block.get("input") or {})))
            elif block.get("type") == "text":
                texts.append(str(block.get("text") or ""))
        return ProviderTurn(text="\n".join(texts).strip(), tool_calls=calls, raw=payload)


class AnthropicMessagesProvider:
    def __init__(self, *, api_key: str, model: str, base_url: str = "https://api.anthropic.com", timeout: float = 120.0, transport: httpx.BaseTransport | None = None, extra: dict[str, Any] | None = None) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.extra = extra or {}
        self.client = httpx.Client(timeout=timeout, transport=transport, headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"})

    def start(self, *, task: str, context: str, tools: list[ToolSpec], instructions: str) -> AnthropicMessagesSession:
        return AnthropicMessagesSession(client=self.client, url=f"{self.base_url}/v1/messages", model=self.model, task=task, context=context, tools=tools, instructions=instructions, extra=self.extra)
