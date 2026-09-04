import json
import os
import time
from urllib import request, error
from typing import Any, Dict, List, Optional

from providers.base import ModelProvider, ModelMetadata, ProviderResponse

# ponytail: Hardened Dialagram / Nexum Router Provider Integration.
# Supports dynamic catalog discovery, secret hygiene, and truthful operational status.
# SECURITY: API keys are runtime configuration only (DIALAGRAM_API_KEY / NEXUM_API_KEY).
# No hardcoded defaults — see STUDY-011 §20 credential hygiene.

DIALAGRAM_DEFAULT_KEY = None
DIALAGRAM_BASE_URL = "https://dialagram.me/router/v1"

MODELS_CATALOG = {
    "qwen-3.8-max": ModelMetadata(
        provider="dialagram",
        model_id="qwen-3.8-max",
        context_window=256000,
        supports_tools=True,
        supports_reasoning=True,
        pricing_per_million_input=0.0,
        pricing_per_million_output=0.0,
        availability="ACTIVE",
        operational_status="LIVE_CAPABLE_UNVERIFIED",
        source="https://dialagram.me/#models"
    ),
    "deepseek-v4": ModelMetadata(
        provider="dialagram",
        model_id="deepseek-v4",
        context_window=128000,
        supports_tools=True,
        supports_reasoning=True,
        pricing_per_million_input=0.0,
        pricing_per_million_output=0.0,
        availability="ACTIVE",
        operational_status="LIVE_CAPABLE_UNVERIFIED",
        source="https://dialagram.me/#models"
    ),
    "xiaomi-mimo-2.5": ModelMetadata(
        provider="dialagram",
        model_id="xiaomi-mimo-2.5",
        context_window=64000,
        supports_tools=True,
        supports_reasoning=False,
        pricing_per_million_input=0.0,
        pricing_per_million_output=0.0,
        availability="ACTIVE",
        operational_status="LIVE_CAPABLE_UNVERIFIED",
        source="https://dialagram.me/#models"
    ),
    "tencent-hy3": ModelMetadata(
        provider="dialagram",
        model_id="tencent-hy3",
        context_window=128000,
        supports_tools=True,
        supports_reasoning=True,
        pricing_per_million_input=0.0,
        pricing_per_million_output=0.0,
        availability="ACTIVE",
        operational_status="LIVE_CAPABLE_UNVERIFIED",
        source="https://dialagram.me/#models"
    ),
    "meta-muse-spark-1.2": ModelMetadata(
        provider="dialagram",
        model_id="meta-muse-spark-1.2",
        context_window=200000,
        supports_tools=True,
        supports_reasoning=True,
        pricing_per_million_input=0.0,
        pricing_per_million_output=0.0,
        availability="ACTIVE",
        operational_status="LIVE_CAPABLE_UNVERIFIED",
        source="https://dialagram.me/#models"
    )
}

class DialagramProvider(ModelProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: str = DIALAGRAM_BASE_URL):
        super().__init__(provider_name="dialagram", default_model="qwen-3.8-max", initial_status="LIVE_CAPABLE_UNVERIFIED")
        # Environment-first secret resolution
        self.api_key = api_key or os.environ.get("DIALAGRAM_API_KEY") or os.environ.get("NEXUM_API_KEY") or DIALAGRAM_DEFAULT_KEY
        self.base_url = base_url.rstrip("/")
        self._discovered_catalog = dict(MODELS_CATALOG)

    def get_supported_models(self) -> Dict[str, ModelMetadata]:
        return self._discovered_catalog

    def discover_models(self) -> Dict[str, ModelMetadata]:
        """Queries router models endpoint dynamically, falling back to cached snapshot."""
        if not self.api_key:
            return self._discovered_catalog

        try:
            req = request.Request(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}", "User-Agent": "JonasAbde-InHouseAgent/1.0"}
            )
            with request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            items = data.get("data", [])
            for item in items:
                m_id = item.get("id")
                if m_id and m_id not in self._discovered_catalog:
                    self._discovered_catalog[m_id] = ModelMetadata(
                        provider="dialagram",
                        model_id=m_id,
                        context_window=item.get("context_window", 128000),
                        supports_tools=True,
                        supports_reasoning=True,
                        availability="ACTIVE",
                        operational_status="LIVE_CAPABLE_UNVERIFIED",
                        source="dialagram_live_discovery"
                    )
        except Exception:
            # Fall back gracefully to cached snapshot
            pass
        return self._discovered_catalog

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
            content = f"[Dialagram Sim: {model_id}] Formulated plan with verified constraints."
            latency = (time.time() - t0) * 1000.0
            return ProviderResponse(
                content=content,
                tool_calls=[],
                prompt_tokens=len(prompt.split()) + len(system_prompt.split()),
                completion_tokens=25,
                total_tokens=len(prompt.split()) + 25,
                cost_usd=0.0,
                latency_ms=latency,
                provider=self.provider_name,
                model_id=model_id,
                is_live=False
            )

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "JonasAbde-InHouseAgent/1.0"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        if tools:
            payload["tools"] = tools

        try:
            req = request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            latency = (time.time() - t0) * 1000.0

            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {})
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])

            usage = data.get("usage", {})
            p_tok = usage.get("prompt_tokens", len(prompt.split()))
            c_tok = usage.get("completion_tokens", len(content.split()))

            # Live request succeeded! Update truthful operational status
            self.operational_status = "LIVE_VERIFIED"

            return ProviderResponse(
                content=content,
                tool_calls=tool_calls,
                prompt_tokens=p_tok,
                completion_tokens=c_tok,
                total_tokens=p_tok + c_tok,
                cost_usd=0.0,  # Included in flat $5.50/wk router plan
                latency_ms=latency,
                provider=self.provider_name,
                model_id=model_id,
                is_live=True,
                raw_response=data
            )
        except Exception as e:
            latency = (time.time() - t0) * 1000.0
            # Mask sensitive API key in any error string
            clean_err = str(e)
            if self.api_key and self.api_key in clean_err:
                clean_err = clean_err.replace(self.api_key, "[REDACTED_API_KEY]")

            return ProviderResponse(
                content=f"[Dialagram Live Error: {clean_err} - Offline Simulation Fallback]",
                tool_calls=[],
                prompt_tokens=len(prompt.split()),
                completion_tokens=20,
                total_tokens=len(prompt.split()) + 20,
                cost_usd=0.0,
                latency_ms=latency,
                provider=self.provider_name,
                model_id=model_id,
                is_live=False,
                raw_response={"error": clean_err}
            )
