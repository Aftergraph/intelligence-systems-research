from __future__ import annotations

import json
import os
import re
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable

import yaml

from .types import ModelProfile

_ENV = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-(.*?))?\}")


def _expand(value: Any) -> Any:
    if isinstance(value, str):
        def repl(match: re.Match[str]) -> str:
            name, default = match.group(1), match.group(2)
            return os.environ.get(name, default or "")
        return _ENV.sub(repl, value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


class ModelRegistry:
    """Data-driven model/provider catalog.

    Models are *not* frontier by default. Frontier eligibility must be explicitly declared
    by configuration/allowlist before the coding router can see a model.
    """

    def __init__(self, models: Iterable[ModelProfile] = ()) -> None:
        self.models = list(models)
        aliases = [m.alias for m in self.models]
        if len(set(aliases)) != len(aliases):
            raise ValueError("Model aliases must be unique")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ModelRegistry":
        payload = _expand(payload)
        raw_models = payload.get("models") or {}
        if isinstance(raw_models, list):
            iterable = [(str(m.get("alias") or m.get("model")), m) for m in raw_models]
        elif isinstance(raw_models, dict):
            iterable = list(raw_models.items())
        else:
            raise TypeError("models must be a mapping or list")
        models: list[ModelProfile] = []
        known = {
            "provider", "model", "tier", "transport", "base_url", "api_key_env",
            "context_window", "max_input_tokens", "supports_tools", "reasoning_effort",
        }
        for alias, raw in iterable:
            if not isinstance(raw, dict) or not raw.get("model"):
                continue
            metadata = {k: v for k, v in raw.items() if k not in known}
            context_window = raw.get("context_window") or raw.get("max_input_tokens")
            models.append(
                ModelProfile(
                    alias=str(alias),
                    provider=str(raw.get("provider") or "custom"),
                    model=str(raw["model"]),
                    tier=str(raw.get("tier") or "unclassified"),
                    transport=str(raw.get("transport") or "openai_compatible"),
                    base_url=raw.get("base_url"),
                    api_key_env=raw.get("api_key_env"),
                    context_window=int(context_window) if context_window else None,
                    supports_tools=bool(raw.get("supports_tools", True)),
                    reasoning_effort=raw.get("reasoning_effort"),
                    metadata=metadata,
                )
            )
        return cls(models)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ModelRegistry":
        with Path(path).open("r", encoding="utf-8") as fh:
            payload = yaml.safe_load(fh) or {}
        return cls.from_dict(payload)

    @classmethod
    def from_litellm_catalog(cls, path: str | Path) -> "ModelRegistry":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("LiteLLM catalog must be a JSON object")
        models: list[ModelProfile] = []
        for model_id, meta in payload.items():
            if not isinstance(meta, dict):
                continue
            provider = str(meta.get("litellm_provider") or meta.get("provider") or model_id.split("/", 1)[0])
            context = meta.get("max_input_tokens") or meta.get("max_tokens")
            models.append(
                ModelProfile(
                    alias=str(model_id),
                    provider=provider,
                    model=str(model_id),
                    tier="unclassified",
                    transport="litellm",
                    context_window=int(context) if context else None,
                    supports_tools=bool(meta.get("supports_function_calling", meta.get("supports_tools", True))),
                    metadata=dict(meta),
                )
            )
        return cls(models)

    def with_frontier_aliases(self, aliases: Iterable[str]) -> "ModelRegistry":
        frontier = {str(alias) for alias in aliases}
        return ModelRegistry(
            replace(model, tier="frontier") if model.alias in frontier else model
            for model in self.models
        )

    def merged(self, other: "ModelRegistry") -> "ModelRegistry":
        by_alias = {model.alias: model for model in self.models}
        by_alias.update({model.alias: model for model in other.models})
        return ModelRegistry(by_alias.values())

    def eligible(self, *, frontier_required: bool = True, require_tools: bool = True) -> list[ModelProfile]:
        return [
            model
            for model in self.models
            if (model.is_frontier or not frontier_required)
            and (model.supports_tools or not require_tools)
        ]

    def by_alias(self, alias: str) -> ModelProfile:
        for model in self.models:
            if model.alias == alias:
                return model
        raise KeyError(alias)
