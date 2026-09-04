import json
import os
import time
from typing import Any, Dict, List, Optional

from providers.base import ModelProvider, ModelMetadata, ProviderResponse

ANTHROPIC_MODELS = {
    "claude-3-7-sonnet-20250219": ModelMetadata("anthropic", "claude-3-7-sonnet-20250219", 200000, True, True, 3.00, 15.00, "ACTIVE"),
    "claude-3-5-sonnet-20241022": ModelMetadata("anthropic", "claude-3-5-sonnet-20241022", 200000, True, False, 3.00, 15.00, "ACTIVE"),
    "claude-3-5-haiku-20241022": ModelMetadata("anthropic", "claude-3-5-haiku-20241022", 200000, True, False, 0.80, 4.00, "ACTIVE")
}

class AnthropicProvider(ModelProvider):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("anthropic", "claude-3-7-sonnet-20250219")
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    def get_supported_models(self) -> Dict[str, ModelMetadata]:
        return ANTHROPIC_MODELS

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        dry_run: bool = False
    ) -> ProviderResponse:
        model_id = model or self.default_model
        t0 = time.time()
        return ProviderResponse(
            content=f"[Anthropic Sim: {model_id}] Structured plan with verified invariants.",
            tool_calls=[],
            prompt_tokens=len(prompt.split()) + 20,
            completion_tokens=30,
            total_tokens=len(prompt.split()) + 50,
            cost_usd=0.00015,
            latency_ms=(time.time() - t0) * 1000.0,
            provider="anthropic",
            model_id=model_id,
            is_live=False
        )
