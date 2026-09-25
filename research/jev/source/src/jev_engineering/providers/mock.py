from __future__ import annotations

from typing import Any

from ..types import ModelProfile, ProviderTurn, ToolCall, ToolSpec


class ScriptedSession:
    def __init__(self, turns: list[dict[str, Any]]) -> None:
        self.turns = iter(turns)
        self.tool_results: list[dict[str, Any]] = []

    def step(self, tool_results: dict[str, Any] | None = None) -> ProviderTurn:
        if tool_results:
            self.tool_results.append(tool_results)
        raw = next(self.turns)
        calls = [
            ToolCall(
                id=str(c.get("id") or f"call-{i}"),
                name=str(c["name"]),
                arguments=dict(c.get("arguments") or {}),
            )
            for i, c in enumerate(raw.get("tool_calls") or [])
        ]
        return ProviderTurn(text=str(raw.get("text") or ""), tool_calls=calls, raw=raw)


class ScriptedProviderFactory:
    def __init__(self, *, turns: list[dict[str, Any]]) -> None:
        self.turns = turns
        self.created_profiles: list[ModelProfile] = []

    def create(
        self,
        profile: ModelProfile,
        *,
        task: str,
        context: str,
        tools: list[ToolSpec],
        instructions: str,
    ) -> ScriptedSession:
        self.created_profiles.append(profile)
        return ScriptedSession(list(self.turns))
