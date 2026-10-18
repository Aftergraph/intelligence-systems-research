from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import httpx

from ..types import ProviderTurn, ToolCall, ToolSpec


class GoogleGenerateContentSession:
    def __init__(self, *, client: httpx.Client, base_url: str, api_key: str, model: str, task: str, context: str, tools: list[ToolSpec], instructions: str, extra: dict[str, Any] | None = None) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.tools = tools
        self.instructions = instructions
        self.extra = extra or {}
        self.contents: list[dict[str, Any]] = [{"role": "user", "parts": [{"text": f"TASK\n{task}\n\nSELECTED CONTEXT\n{context}"}]}]
        self.pending_call_names: dict[str, str] = {}

    def step(self, tool_results: dict[str, Any] | None = None) -> ProviderTurn:
        if tool_results:
            parts = []
            for call_id, result in tool_results.items():
                name = self.pending_call_names.get(call_id)
                if not name:
                    raise RuntimeError(f"Unknown Google function call id {call_id!r}")
                parts.append({
                    "functionResponse": {
                        "call_id": call_id,
                        "name": name,
                        "response": {"result": result},
                    }
                })
            self.contents.append({"role": "user", "parts": parts})
        declarations = [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in self.tools
        ]
        body: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": self.instructions}]},
            "contents": self.contents,
            "tools": [{"functionDeclarations": declarations}],
        }
        body.update(self.extra)
        url = f"{self.base_url}/v1beta/models/{quote(self.model, safe='')}:generateContent?key={self.api_key}"
        r = self.client.post(url, json=body)
        r.raise_for_status()
        payload = r.json()
        candidate = (payload.get("candidates") or [{}])[0]
        content = candidate.get("content") or {}
        if content:
            self.contents.append(content)
        calls: list[ToolCall] = []
        texts: list[str] = []
        for i, part in enumerate(content.get("parts") or []):
            if "functionCall" in part:
                fn = part["functionCall"]
                name = str(fn.get("name"))
                call_id = str(fn.get("call_id") or fn.get("id") or f"{name}::{len(self.contents)}-{i}")
                self.pending_call_names[call_id] = name
                calls.append(ToolCall(call_id, name, dict(fn.get("args") or {})))
            elif "text" in part:
                texts.append(str(part["text"]))
        return ProviderTurn(text="\n".join(texts).strip(), tool_calls=calls, raw=payload)


class GoogleGenerateContentProvider:
    def __init__(self, *, api_key: str, model: str, base_url: str = "https://generativelanguage.googleapis.com", timeout: float = 120.0, transport: httpx.BaseTransport | None = None, extra: dict[str, Any] | None = None) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.extra = extra or {}
        self.client = httpx.Client(timeout=timeout, transport=transport, headers={"content-type": "application/json"})

    def start(self, *, task: str, context: str, tools: list[ToolSpec], instructions: str) -> GoogleGenerateContentSession:
        return GoogleGenerateContentSession(client=self.client, base_url=self.base_url, api_key=self.api_key, model=self.model, task=task, context=context, tools=tools, instructions=instructions, extra=self.extra)
