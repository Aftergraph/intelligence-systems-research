import json
import os
import time
from urllib import request
from typing import Any, Dict, List, Optional
from providers.base import ModelProvider, ModelMetadata, ProviderResponse
from providers.http_failure import provider_error_snapshot

OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
OPENROUTER_MODELS={
    "google/gemma-4-31b-it": ModelMetadata("openrouter","google/gemma-4-31b-it",262144,True,False,availability="ACTIVE",operational_status="LIVE_CAPABLE_UNVERIFIED",source="openrouter_live_catalog"),
    "z-ai/glm-5.2": ModelMetadata("openrouter","z-ai/glm-5.2",256000,True,False,availability="ACTIVE",operational_status="LIVE_CAPABLE_UNVERIFIED",source="openrouter_live_catalog"),
}
class OpenRouterProvider(ModelProvider):
    def __init__(self, api_key: Optional[str]=None, base_url: str=OPENROUTER_BASE_URL):
        super().__init__("openrouter","google/gemma-4-31b-it")
        self.api_key=api_key or os.environ.get("OPENROUTER_API_KEY")
        self.base_url=base_url.rstrip("/")

    def get_supported_models(self)->Dict[str,ModelMetadata]:
        return OPENROUTER_MODELS

    def discover_models(self)->Dict[str,ModelMetadata]:
        if not self.api_key: return self.get_supported_models()
        req=request.Request(f"{self.base_url}/models",headers={"Authorization":f"Bearer {self.api_key}","User-Agent":"Aftergraph-Provider/1.0"})
        try:
            with request.urlopen(req,timeout=15) as resp:
                payload=json.loads(resp.read().decode("utf-8"))
            out={}
            for item in payload.get("data",[]):
                mid=item.get("id")
                if mid:
                    out[mid]=ModelMetadata("openrouter",mid,int(item.get("context_length") or 128000),True,False,availability="ACTIVE",operational_status="LIVE_CAPABLE_UNVERIFIED",source="openrouter_live_catalog")
            return out or self.get_supported_models()
        except Exception:
            return self.get_supported_models()

    def generate(self,prompt:str,system_prompt:str="",model:Optional[str]=None,tools:Optional[List[Dict[str,Any]]]=None,max_tokens:int=2048,temperature:float=0.2,dry_run:bool=False)->ProviderResponse:
        model_id=model or self.default_model
        t0=time.time()
        if dry_run or not self.api_key:
            return ProviderResponse(content=f"[OpenRouter Dry Run: {model_id}]",prompt_tokens=0,completion_tokens=0,total_tokens=0,cost_usd=0.0,latency_ms=(time.time()-t0)*1000,provider="openrouter",model_id=model_id,is_live=False)
        payload={"model":model_id,"messages":[*([{"role":"system","content":system_prompt}] if system_prompt else []),{"role":"user","content":prompt}],"max_tokens":max_tokens,"temperature":temperature}
        if tools: payload["tools"]=tools
        req=request.Request(f"{self.base_url}/chat/completions",data=json.dumps(payload).encode("utf-8"),headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json","User-Agent":"Aftergraph-Provider/1.0"},method="POST")
        try:
            with request.urlopen(req,timeout=45) as resp:
                data=json.loads(resp.read().decode("utf-8"))
            choice=(data.get("choices") or [{}])[0]
            msg=choice.get("message",{})
            content=msg.get("content") or ""
            usage=data.get("usage") or {}
            pt=int(usage.get("prompt_tokens") or 0); ct=int(usage.get("completion_tokens") or 0)
            self.operational_status="LIVE_VERIFIED"
            return ProviderResponse(content=content,tool_calls=msg.get("tool_calls") or [],prompt_tokens=pt,completion_tokens=ct,total_tokens=int(usage.get("total_tokens") or pt+ct),cost_usd=float(usage.get("cost") or 0.0),latency_ms=(time.time()-t0)*1000,provider="openrouter",model_id=model_id,is_live=True,raw_response=data)
        except Exception as exc:
            failure=provider_error_snapshot(exc,self.api_key)
            return ProviderResponse(content="",prompt_tokens=0,completion_tokens=0,total_tokens=0,cost_usd=0.0,latency_ms=(time.time()-t0)*1000,provider="openrouter",model_id=model_id,is_live=False,raw_response={"failure":failure})

class LocalProvider(ModelProvider):
    def __init__(self,endpoint:str="http://localhost:11434"):
        super().__init__("local_ollama","qwen2.5-coder:7b",initial_status="LOCAL"); self.endpoint=endpoint
    def get_supported_models(self)->Dict[str,ModelMetadata]:
        return {"qwen2.5-coder:7b":ModelMetadata("local_ollama","qwen2.5-coder:7b",32768,True,False,0.0,0.0,"ACTIVE",operational_status="LOCAL")}
    def generate(self,prompt:str,system_prompt:str="",model:Optional[str]=None,tools:Optional[List[Dict[str,Any]]]=None,max_tokens:int=2048,temperature:float=0.2,dry_run:bool=False)->ProviderResponse:
        model_id=model or self.default_model
        return ProviderResponse(content=f"[Local Stub: {model_id}]",prompt_tokens=0,completion_tokens=0,total_tokens=0,cost_usd=0.0,latency_ms=0.0,provider="local_ollama",model_id=model_id,is_live=False)
