from __future__ import annotations

import os
from typing import Any

from ..types import ModelProfile, ToolSpec
from .anthropic_messages import AnthropicMessagesProvider
from .google_generate_content import GoogleGenerateContentProvider
from .litellm_bridge import LiteLLMProvider
from .openai_compatible import OpenAICompatibleProvider
from .openai_responses import OpenAIResponsesProvider


_DEFAULT_BASE_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "mistral": "https://api.mistral.ai/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "xai": "https://api.x.ai/v1",
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "cerebras": "https://api.cerebras.ai/v1",
    "perplexity": "https://api.perplexity.ai",
    "ollama": "http://localhost:11434/v1",
    "vllm": "http://localhost:8000/v1",
    "dialagram": "https://dialagram.me/router/v1",
    "nexum": "https://dialagram.me/router/v1",
}

_DEFAULT_KEY_ENVS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "xai": "XAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "together": "TOGETHER_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "dialagram": "DIALAGRAM_API_KEY",
    "nexum": "DIALAGRAM_API_KEY",
}


class LiveProviderFactory:
    """Creates native or compatibility sessions from declarative model profiles.

    Unknown providers remain usable via either `openai_compatible` (base_url
    required) or the optional `litellm` transport. This avoids a closed provider
    enum and keeps the catalog extensible as models appear.
    """

    def _api_key(self, profile: ModelProfile) -> str:
        env = profile.api_key_env or _DEFAULT_KEY_ENVS.get(profile.provider.lower())
        if not env:
            # Local OpenAI-compatible servers commonly need no key.
            if profile.provider.lower() in {"ollama", "vllm", "local"}:
                return ""
            raise RuntimeError(f"No api_key_env configured for provider {profile.provider!r}")
        value = os.environ.get(env, "")
        if not value:
            raise RuntimeError(f"Missing API key environment variable {env} for model {profile.alias}")
        return value

    def create(self, profile: ModelProfile, *, task: str, context: str, tools: list[ToolSpec], instructions: str):
        transport = profile.transport.lower()
        provider = profile.provider.lower()
        extra = dict(profile.metadata.get("request") or {})
        if profile.reasoning_effort and "reasoning" not in extra:
            extra["reasoning"] = {"effort": profile.reasoning_effort}
        if transport == "openai_responses":
            impl = OpenAIResponsesProvider(
                api_key=self._api_key(profile),
                model=profile.model,
                base_url=profile.base_url or "https://api.openai.com/v1",
                extra=extra,
            )
        elif transport == "anthropic_messages":
            impl = AnthropicMessagesProvider(
                api_key=self._api_key(profile),
                model=profile.model,
                base_url=profile.base_url or "https://api.anthropic.com",
                extra=extra,
            )
        elif transport == "google_generate_content":
            impl = GoogleGenerateContentProvider(
                api_key=self._api_key(profile),
                model=profile.model,
                base_url=profile.base_url or "https://generativelanguage.googleapis.com",
                extra=extra,
            )
        elif transport == "litellm":
            # LiteLLM resolves provider-specific credentials itself.
            impl = LiteLLMProvider(model=profile.model, extra=extra)
        elif transport == "openai_compatible":
            base_url = profile.base_url or _DEFAULT_BASE_URLS.get(provider)
            if not base_url:
                raise RuntimeError(f"openai_compatible model {profile.alias!r} requires base_url")
            impl = OpenAICompatibleProvider(
                api_key=self._api_key(profile),
                model=profile.model,
                base_url=base_url,
                extra=extra,
            )
        else:
            raise RuntimeError(f"Unsupported transport {profile.transport!r}")
        return impl.start(task=task, context=context, tools=tools, instructions=instructions)
