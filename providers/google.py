import json
import os
import time
from urllib import request, error
from typing import Any, Dict, List, Optional

from providers.base import ModelProvider, ModelMetadata, ProviderResponse
from providers.http_failure import provider_error_snapshot

GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GOOGLE_MODELS = {
    "gemini-2.5-flash": ModelMetadata(
        "google", "gemini-2.5-flash", 1048576, True, True,
        availability="ACTIVE", operational_status="LIVE_CAPABLE_UNVERIFIED",
        source="google_gemini_api_catalog"
    ),
    "gemini-2.5-pro": ModelMetadata(
        "google", "gemini-2.5-pro", 1048576, True, True,
        availability="ACTIVE", operational_status="LIVE_CAPABLE_UNVERIFIED",
        source="google_gemini_api_catalog"
    ),
}

class GoogleProvider(ModelProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: str = GOOGLE_BASE_URL):
        super().__init__("google", "gemini-2.5-flash")
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        self.base_url = base_url.rstrip("/")

    def get_supported_models(self) -> Dict[str, ModelMetadata]:
        return GOOGLE_MODELS

    def discover_models(self) -> Dict[str, ModelMetadata]:
        if not self.api_key:
            return self.get_supported_models()
        req = request.Request(
            f"{self.base_url}/models?key={self.api_key}",
            headers={"User-Agent": "Aftergraph-Provider/1.0"},
        )
        try:
            with request.urlopen(req, timeout=15) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            out: Dict[str, ModelMetadata] = {}
            for item in payload.get("models", []):
                name = item.get("name", "")
                mid = name.removeprefix("models/")
                methods = set(item.get("supportedGenerationMethods", []))
                if mid:
                    out[mid] = ModelMetadata(
                        provider="google",
                        model_id=mid,
                        context_window=item.get("inputTokenLimit", 128000),
                        supports_tools=True,
                        supports_reasoning=True,
                        availability="ACTIVE",
                        operational_status="LIVE_CAPABLE_UNVERIFIED",
                        source="google_live_catalog",
                        provider_metadata={"supported_generation_methods": sorted(methods)},
                    )
            return out or self.get_supported_models()
        except Exception:
            return self.get_supported_models()

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        dry_run: bool = False,
    ) -> ProviderResponse:
        model_id = model or self.default_model
        t0 = time.time()
        if dry_run or not self.api_key:
            return ProviderResponse(
                content=f"[Google Dry Run: {model_id}]",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_usd=0.0,
                latency_ms=(time.time() - t0) * 1000.0,
                provider="google",
                model_id=model_id,
                is_live=False,
            )

        endpoint = f"{self.base_url}/models/{model_id}:generateContent?key={self.api_key}"
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "thinkingConfig": {
                    "thinkingBudget": 0 if model_id == "gemini-2.5-flash" else -1
                },
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Aftergraph-Provider/1.0"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
            content = "".join(
                p.get("text", "")
                for p in parts
                if isinstance(p, dict) and not p.get("thought", False)
            )
            usage = data.get("usageMetadata", {})
            prompt_tokens = int(usage.get("promptTokenCount", 0) or 0)
            completion_tokens = int(usage.get("candidatesTokenCount", 0) or 0)
            self.operational_status = "LIVE_VERIFIED"
            return ProviderResponse(
                content=content,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=int(usage.get("totalTokenCount", prompt_tokens + completion_tokens) or 0),
                cost_usd=0.0,
                latency_ms=(time.time() - t0) * 1000.0,
                provider="google",
                model_id=model_id,
                is_live=True,
                raw_response=data,
            )
        except Exception as exc:
            failure = provider_error_snapshot(exc, self.api_key)
            return ProviderResponse(
                content="",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_usd=0.0,
                latency_ms=(time.time() - t0) * 1000.0,
                provider="google",
                model_id=model_id,
                is_live=False,
                raw_response={"failure": failure},
            )
