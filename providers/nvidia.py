import json
import os
import time
from urllib import request
from typing import Any, Dict, List, Optional

from providers.base import ModelProvider, ModelMetadata, ProviderResponse
from providers.http_failure import provider_error_snapshot

NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1"
NVIDIA_MODELS={
 "nvidia/nemotron-3-ultra-550b-a55b":ModelMetadata(provider="nvidia",model_id="nvidia/nemotron-3-ultra-550b-a55b",context_window=1_000_000,supports_tools=True,supports_reasoning=True,availability="ACTIVE",operational_status="LIVE_CAPABLE_UNVERIFIED",source="nvidia_live_catalog"),
 "nvidia/nemotron-3-super-120b-a12b":ModelMetadata(provider="nvidia",model_id="nvidia/nemotron-3-super-120b-a12b",context_window=1_000_000,supports_tools=True,supports_reasoning=True,availability="ACTIVE",operational_status="LIVE_CAPABLE_UNVERIFIED",source="nvidia_live_catalog"),
}
class NvidiaProvider(ModelProvider):
 def __init__(self,api_key:Optional[str]=None,base_url:str=NVIDIA_BASE_URL):
  super().__init__("nvidia","nvidia/nemotron-3-ultra-550b-a55b")
  self.api_key=api_key or os.environ.get("NVIDIA_API_KEY")
  self.base_url=base_url.rstrip("/")
 def get_supported_models(self)->Dict[str,ModelMetadata]: return NVIDIA_MODELS
 def generate(self,prompt:str,system_prompt:str="",model:Optional[str]=None,tools:Optional[List[Dict[str,Any]]]=None,max_tokens:int=2048,temperature:float=0.2,dry_run:bool=False)->ProviderResponse:
  model_id=model or self.default_model; t0=time.time()
  if dry_run or not self.api_key:
   return ProviderResponse(content=f"[NVIDIA Dry Run: {model_id}]",provider="nvidia",model_id=model_id,is_live=False,latency_ms=(time.time()-t0)*1000)
  messages=[]
  if system_prompt: messages.append({"role":"system","content":system_prompt})
  messages.append({"role":"user","content":prompt})
  payload={"model":model_id,"messages":messages,"max_tokens":max_tokens,"temperature":temperature,"extra_body":{"chat_template_kwargs":{"enable_thinking":False}}}
  if tools: payload["tools"]=tools
  req=request.Request(f"{self.base_url}/chat/completions",data=json.dumps(payload).encode(),headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json","User-Agent":"Aftergraph-Provider/1.0"},method="POST")
  try:
   with request.urlopen(req,timeout=60) as resp: data=json.loads(resp.read().decode())
   msg=((data.get("choices") or [{}])[0].get("message") or {})
   usage=data.get("usage") or {}; pt=int(usage.get("prompt_tokens") or 0); ct=int(usage.get("completion_tokens") or 0)
   self.operational_status="LIVE_VERIFIED"
   return ProviderResponse(content=msg.get("content") or "",tool_calls=msg.get("tool_calls") or [],prompt_tokens=pt,completion_tokens=ct,total_tokens=int(usage.get("total_tokens") or pt+ct),cost_usd=0.0,latency_ms=(time.time()-t0)*1000,provider="nvidia",model_id=model_id,is_live=True,raw_response=data)
  except Exception as exc:
   return ProviderResponse(content="",provider="nvidia",model_id=model_id,is_live=False,latency_ms=(time.time()-t0)*1000,raw_response={"failure":provider_error_snapshot(exc,self.api_key)})
