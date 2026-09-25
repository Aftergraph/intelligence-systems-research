from __future__ import annotations

import json
from typing import Any

from ..types import ProviderTurn, ToolCall, ToolSpec


class LiteLLMSession:
    def __init__(self, *, model: str, task: str, context: str, tools: list[ToolSpec], instructions: str, extra: dict[str, Any] | None = None) -> None:
        try:
            import litellm  # type: ignore
        except ImportError as exc:
            raise RuntimeError("LiteLLM transport requires `pip install 'aftergraph-jev-engineering[all-providers]'`") from exc
        self.litellm = litellm
        self.model = model
        self.extra = extra or {}
        self.tools = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}} for t in tools]
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": f"TASK\n{task}\n\nSELECTED CONTEXT\n{context}"},
        ]

    def step(self, tool_results: dict[str, Any] | None = None) -> ProviderTurn:
        for call_id, result in (tool_results or {}).items():
            self.messages.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(result, ensure_ascii=False)})
        response = self.litellm.completion(model=self.model, messages=self.messages, tools=self.tools, tool_choice="auto", **self.extra)
        message = response.choices[0].message
        wire = message.model_dump() if hasattr(message, "model_dump") else dict(message)
        self.messages.append(wire)
        calls: list[ToolCall] = []
        for item in wire.get("tool_calls") or []:
            fn = item.get("function") or {}
            args = fn.get("arguments") or "{}"
            if isinstance(args, str):
                args = json.loads(args)
            calls.append(ToolCall(str(item.get("id")), str(fn.get("name")), dict(args)))
        return ProviderTurn(text=str(wire.get("content") or ""), tool_calls=calls, raw={"litellm": True})


class LiteLLMProvider:
    def __init__(self, *, model: str, extra: dict[str, Any] | None = None) -> None:
        self.model = model
        self.extra = extra or {}

    def start(self, *, task: str, context: str, tools: list[ToolSpec], instructions: str) -> LiteLLMSession:
        return LiteLLMSession(model=self.model, task=task, context=context, tools=tools, instructions=instructions, extra=self.extra)
