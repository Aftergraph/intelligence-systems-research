from __future__ import annotations

import json
from typing import Any

import httpx

from ..types import ProviderTurn, ToolCall, ToolSpec


class OpenAICompatibleSession:
    def __init__(self, *, client: httpx.Client, url: str, model: str, task: str, context: str, tools: list[ToolSpec], instructions: str, extra: dict[str, Any] | None = None) -> None:
        self.client = client
        self.url = url
        self.model = model
        self.tools = tools
        self.extra = extra or {}
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": f"TASK\n{task}\n\nSELECTED CONTEXT\n{context}"},
        ]
        self.pending_calls: dict[str, dict[str, Any]] = {}

    def step(self, tool_results: dict[str, Any] | None = None) -> ProviderTurn:
        for call_id, result in (tool_results or {}).items():
            self.messages.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(result, ensure_ascii=False)})
        wire_tools = [
            {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
            for t in self.tools
        ]
        body = {"model": self.model, "messages": self.messages, "tools": wire_tools, "tool_choice": "auto"}
        body.update(self.extra)
        r = self.client.post(self.url, json=body)
        r.raise_for_status()
        payload = r.json()
        message = (payload.get("choices") or [{}])[0].get("message") or {}
        self.messages.append(message)
        calls: list[ToolCall] = []
        for item in message.get("tool_calls") or []:
            fn = item.get("function") or {}
            args = fn.get("arguments") or "{}"
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"_raw": args}
            calls.append(ToolCall(str(item.get("id")), str(fn.get("name")), dict(args)))
        content = message.get("content") or ""
        if isinstance(content, list):
            content = "\n".join(str(x.get("text", "")) for x in content if isinstance(x, dict))
        return ProviderTurn(text=str(content), tool_calls=calls, raw=payload)


class OpenAICompatibleProvider:
    def __init__(self, *, api_key: str, model: str, base_url: str, timeout: float = 120.0, transport: httpx.BaseTransport | None = None, extra: dict[str, Any] | None = None) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.extra = extra or {}
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self.client = httpx.Client(timeout=timeout, transport=transport, headers=headers)

    def start(self, *, task: str, context: str, tools: list[ToolSpec], instructions: str) -> OpenAICompatibleSession:
        return OpenAICompatibleSession(client=self.client, url=f"{self.base_url}/chat/completions", model=self.model, task=task, context=context, tools=tools, instructions=instructions, extra=self.extra)
