import json
import time
from urllib import request
from typing import Any, Dict, List, Optional

from providers.base import ModelProvider, ModelMetadata, ProviderResponse
from providers.http_failure import provider_error_snapshot

OLLAMA_LOCAL_BASE_URL="http://127.0.0.1:11434"
OLLAMA_LOCAL_MODELS={
    "qwen3.6:latest": ModelMetadata(
        provider="ollama-local",
        model_id="qwen3.6:latest",
        context_window=262144,
        supports_tools=True,
        supports_reasoning=True,
        availability="ACTIVE",
        operational_status="LOCAL",
        source="local_ollama_inventory",
    )
}

class OllamaLocalProvider(ModelProvider):
    def __init__(self, base_url: str = OLLAMA_LOCAL_BASE_URL):
        super().__init__("ollama-local","qwen3.6:latest",initial_status="LOCAL")
        self.base_url=base_url.rstrip("/")

    def get_supported_models(self)->Dict[str,ModelMetadata]:
        return OLLAMA_LOCAL_MODELS

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        tools: Optional[List[Dict[str,Any]]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
        dry_run: bool = False,
    )->ProviderResponse:
        model_id=model or self.default_model
        t0=time.time()
        if dry_run:
            return ProviderResponse(
                content=f"[Ollama Local Dry Run: {model_id}]",
                provider="ollama-local",model_id=model_id,is_live=False,
                latency_ms=(time.time()-t0)*1000,
            )
        messages=[]
        if system_prompt:
            messages.append({"role":"system","content":system_prompt})
        messages.append({"role":"user","content":prompt})
        payload={
            "model":model_id,
            "messages":messages,
            "stream":False,
            "think":False,
            "options":{"temperature":temperature,"num_predict":max_tokens},
        }
        if tools:
            payload["tools"]=tools
        req=request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type":"application/json","User-Agent":"Aftergraph-Provider/1.0"},
            method="POST",
        )
        try:
            with request.urlopen(req,timeout=180) as resp:
                data=json.loads(resp.read().decode("utf-8"))
            msg=data.get("message") or {}
            pt=int(data.get("prompt_eval_count") or 0)
            ct=int(data.get("eval_count") or 0)
            self.operational_status="LOCAL"
            return ProviderResponse(
                content=msg.get("content") or "",
                tool_calls=msg.get("tool_calls") or [],
                prompt_tokens=pt,
                completion_tokens=ct,
                total_tokens=pt+ct,
                cost_usd=0.0,
                latency_ms=(time.time()-t0)*1000,
                provider="ollama-local",
                model_id=model_id,
                is_live=True,
                raw_response={
                    "done":data.get("done"),
                    "done_reason":data.get("done_reason"),
                    "thinking_present":bool(msg.get("thinking")),
                    "total_duration":data.get("total_duration"),
                },
            )
        except Exception as exc:
            return ProviderResponse(
                content="",
                provider="ollama-local",model_id=model_id,is_live=False,
                latency_ms=(time.time()-t0)*1000,
                raw_response={"failure":provider_error_snapshot(exc,None)},
            )
