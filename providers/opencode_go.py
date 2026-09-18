import json,os,time
from urllib import request
from typing import Any,Dict,List,Optional
from providers.base import ModelProvider,ModelMetadata,ProviderResponse
from providers.http_failure import provider_error_snapshot

OPENCODE_GO_BASE_URL="https://opencode.ai/zen/go/v1"
OPENCODE_GO_MODELS={
 "deepseek-v4-flash":ModelMetadata(provider="opencode_go",model_id="deepseek-v4-flash",context_window=262144,supports_tools=True,supports_reasoning=True,availability="ACTIVE",operational_status="LIVE_CAPABLE_UNVERIFIED",source="opencode_go_live_catalog"),
 "glm-5.2":ModelMetadata(provider="opencode_go",model_id="glm-5.2",context_window=262144,supports_tools=True,supports_reasoning=True,availability="ACTIVE",operational_status="LIVE_CAPABLE_UNVERIFIED",source="opencode_go_live_catalog"),
}
class OpenCodeGoProvider(ModelProvider):
 def __init__(self,api_key:Optional[str]=None,base_url:str=OPENCODE_GO_BASE_URL,session_id:Optional[str]=None):
  super().__init__("opencode_go","deepseek-v4-flash")
  self.api_key=api_key or os.environ.get("OPENCODE_GO_API_KEY")
  self.base_url=base_url.rstrip("/")
  self.session_id=session_id or os.environ.get("OPENCODE_SESSION_ID") or "aftergraph-study012"
 def get_supported_models(self)->Dict[str,ModelMetadata]: return OPENCODE_GO_MODELS
 def generate(self,prompt:str,system_prompt:str="",model:Optional[str]=None,tools:Optional[List[Dict[str,Any]]]=None,max_tokens:int=2048,temperature:float=0.2,dry_run:bool=False)->ProviderResponse:
  model_id=model or self.default_model;t0=time.time()
  if dry_run or not self.api_key:
   return ProviderResponse(content=f"[OpenCode Go Dry Run: {model_id}]",provider="opencode_go",model_id=model_id,is_live=False,latency_ms=(time.time()-t0)*1000)
  messages=[]
  if system_prompt:messages.append({"role":"system","content":system_prompt})
  messages.append({"role":"user","content":prompt})
  payload={"model":model_id,"messages":messages,"max_tokens":max_tokens,"temperature":temperature,"stream":False}
  if tools:payload["tools"]=tools
  req=request.Request(f"{self.base_url}/chat/completions",data=json.dumps(payload).encode(),headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json","User-Agent":"aftergraph-study012-agent/1.0","x-opencode-session":self.session_id},method="POST")
  try:
   with request.urlopen(req,timeout=60) as resp:data=json.loads(resp.read().decode())
   msg=((data.get("choices") or [{}])[0].get("message") or {})
   usage=data.get("usage") or {};pt=int(usage.get("prompt_tokens") or 0);ct=int(usage.get("completion_tokens") or 0)
   self.operational_status="LIVE_VERIFIED"
   return ProviderResponse(content=msg.get("content") or "",tool_calls=msg.get("tool_calls") or [],prompt_tokens=pt,completion_tokens=ct,total_tokens=int(usage.get("total_tokens") or pt+ct),cost_usd=float(usage.get("cost") or 0.0),latency_ms=(time.time()-t0)*1000,provider="opencode_go",model_id=model_id,is_live=True,raw_response=data)
  except Exception as exc:
   return ProviderResponse(content="",provider="opencode_go",model_id=model_id,is_live=False,latency_ms=(time.time()-t0)*1000,raw_response={"failure":provider_error_snapshot(exc,self.api_key)})
