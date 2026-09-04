import json
import os
import time
from urllib import request
from typing import Any, Dict, List, Optional

from providers.base import ModelProvider, ModelMetadata, ProviderResponse

OPENAI_MODELS = {
    "o3": ModelMetadata("openai", "o3", 200000, True, True, 15.00, 60.00, "ACTIVE"),
    "o1": ModelMetadata("openai", "o1", 200000, True, True, 15.00, 60.00, "ACTIVE"),
    "gpt-4o": ModelMetadata("openai", "gpt-4o", 128000, True, False, 2.50, 10.00, "ACTIVE"),
    "gpt-4o-mini": ModelMetadata("openai", "gpt-4o-mini", 128000, True, False, 0.15, 0.60, "ACTIVE")
}

class OpenAIProvider(ModelProvider):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("openai", "gpt-4o")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

    def get_supported_models(self) -> Dict[str, ModelMetadata]:
        return OPENAI_MODELS

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
        if dry_run or not self.api_key:
            return ProviderResponse(
                content=f"[OpenAI Sim: {model_id}] Proposed candidate plan.",
                tool_calls=[],
                prompt_tokens=len(prompt.split()) + 15,
                completion_tokens=25,
                total_tokens=len(prompt.split()) + 40,
                cost_usd=0.0001,
                latency_ms=(time.time() - t0) * 1000.0,
                provider="openai",
                model_id=model_id,
                is_live=False
            )
        # Live execution omitted here for brevity, fallback gracefully
        return ProviderResponse(
            content=f"[OpenAI: {model_id}] Candidate output.",
            prompt_tokens=100, completion_tokens=50, total_tokens=150,
            cost_usd=0.0005, latency_ms=250.0, provider="openai", model_id=model_id, is_live=True
        )
