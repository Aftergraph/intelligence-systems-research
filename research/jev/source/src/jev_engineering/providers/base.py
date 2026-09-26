from __future__ import annotations

from typing import Any, Protocol

from ..types import ModelProfile, ProviderTurn, ToolSpec


class ProviderSession(Protocol):
    def step(self, tool_results: dict[str, Any] | None = None) -> ProviderTurn: ...


class ProviderFactory(Protocol):
    def create(
        self,
        profile: ModelProfile,
        *,
        task: str,
        context: str,
        tools: list[ToolSpec],
        instructions: str,
    ) -> ProviderSession: ...
