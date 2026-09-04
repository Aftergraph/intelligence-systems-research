import os
import time
from typing import Any, Dict, List, Optional
from providers.base import ModelProvider, ModelMetadata, ProviderResponse

GOOGLE_MODELS = {
    "gemini-2.0-pro": ModelMetadata("google", "gemini-2.0-pro", 1000000, True, True, 1.25, 5.00, "ACTIVE"),
    "gemini-1.5-pro": ModelMetadata("google", "gemini-1.5-pro", 2000000, True, True, 1.25, 5.00, "ACTIVE")
}

class GoogleProvider(ModelProvider):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("google", "gemini-2.0-pro")
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")

    def get_supported_models(self) -> Dict[str, ModelMetadata]:
        return GOOGLE_MODELS

    def generate(self, prompt: str, system_prompt: str = "", model: Optional[str] = None, tools: Optional[List[Dict[str, Any]]] = None, max_tokens: int = 2048, temperature: float = 0.2, dry_run: bool = False) -> ProviderResponse:
        model_id = model or self.default_model
        t0 = time.time()
        return ProviderResponse(
            content=f"[Google Sim: {model_id}] Large-context execution plan.",
            prompt_tokens=len(prompt.split()) + 10,
            completion_tokens=20,
            total_tokens=len(prompt.split()) + 30,
            cost_usd=0.00005,
            latency_ms=(time.time() - t0) * 1000.0,
            provider="google",
            model_id=model_id,
            is_live=False
        )
