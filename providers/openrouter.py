import os
import time
from typing import Any, Dict, List, Optional
from providers.base import ModelProvider, ModelMetadata, ProviderResponse

class OpenRouterProvider(ModelProvider):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("openrouter", "deepseek/deepseek-r1")
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")

    def get_supported_models(self) -> Dict[str, ModelMetadata]:
        return {
            "deepseek/deepseek-r1": ModelMetadata("openrouter", "deepseek/deepseek-r1", 128000, True, True, 0.55, 2.19, "ACTIVE"),
            "anthropic/claude-3.7-sonnet": ModelMetadata("openrouter", "anthropic/claude-3.7-sonnet", 200000, True, True, 3.00, 15.00, "ACTIVE")
        }

    def generate(self, prompt: str, system_prompt: str = "", model: Optional[str] = None, tools: Optional[List[Dict[str, Any]]] = None, max_tokens: int = 2048, temperature: float = 0.2, dry_run: bool = False) -> ProviderResponse:
        model_id = model or self.default_model
        t0 = time.time()
        return ProviderResponse(
            content=f"[OpenRouter Sim: {model_id}] Aggregated reasoning plan.",
            prompt_tokens=len(prompt.split()),
            completion_tokens=25,
            total_tokens=len(prompt.split()) + 25,
            cost_usd=0.00008,
            latency_ms=(time.time() - t0) * 1000.0,
            provider="openrouter",
            model_id=model_id,
            is_live=False
        )

class LocalProvider(ModelProvider):
    def __init__(self, endpoint: str = "http://localhost:11434"):
        super().__init__("local_ollama", "qwen2.5-coder:7b")
        self.endpoint = endpoint

    def get_supported_models(self) -> Dict[str, ModelMetadata]:
        return {
            "qwen2.5-coder:7b": ModelMetadata("local_ollama", "qwen2.5-coder:7b", 32768, True, False, 0.0, 0.0, "ACTIVE"),
            "llama3.1:8b": ModelMetadata("local_ollama", "llama3.1:8b", 128000, False, False, 0.0, 0.0, "ACTIVE")
        }

    def generate(self, prompt: str, system_prompt: str = "", model: Optional[str] = None, tools: Optional[List[Dict[str, Any]]] = None, max_tokens: int = 2048, temperature: float = 0.2, dry_run: bool = False) -> ProviderResponse:
        model_id = model or self.default_model
        t0 = time.time()
        return ProviderResponse(
            content=f"[Local Sim: {model_id}] Local offline inference output.",
            prompt_tokens=len(prompt.split()),
            completion_tokens=20,
            total_tokens=len(prompt.split()) + 20,
            cost_usd=0.0,
            latency_ms=(time.time() - t0) * 1000.0,
            provider="local_ollama",
            model_id=model_id,
            is_live=False
        )
