import json,os,time
from urllib import request
from typing import Any,Dict,List,Optional
from providers.base import ModelProvider,ModelMetadata,ProviderResponse
from providers.http_failure import provider_error_snapshot

HF_BASE_URL="https://router.huggingface.co/v1"
HF_MODELS={
 "openai/gpt-oss-120b:groq":ModelMetadata(provider="hf_groq",model_id="openai/gpt-oss-120b:groq",context_window=131072,supports_tools=True,supports_reasoning=True,availability="ACTIVE",operational_status="LIVE_CAPABLE_UNVERIFIED",source="hf_router_explicit_groq"),
}
class HFGroqProvider(ModelProvider):
 def __init__(self,api_key:Optional[str]=None,base_url:str=HF_BASE_URL):
  super().__init__("hf_groq","openai/gpt-oss-120b:groq")
  self.api_key=api_key or os.environ.get("HF_API_KEY") or os.environ.get("HF_TOKEN")
  self.base_url=base_url.rstrip("/")
 def get_supported_models(self)->Dict[str,ModelMetadata]: return HF_MODELS
 def generate(self,prompt:str,system_prompt:str="",model:Optional[str]=None,tools:Optional[List[Dict[str,Any]]]=None,max_tokens:int=2048,temperature:float=0.2,dry_run:bool=False)->ProviderResponse:
  model_id=model or self.default_model;t0=time.time()
  if not model_id.endswith(":groq"):
   return ProviderResponse(content="",provider="hf_groq",model_id=model_id,is_live=False,raw_response={"failure":{"category":"ROUTING_POLICY","reason":"backend_suffix_must_be_groq"}},latency_ms=(time.time()-t0)*1000)
  if dry_run or not self.api_key:
   return ProviderResponse(content=f"[HF Groq Dry Run: {model_id}]",provider="hf_groq",model_id=model_id,is_live=False,latency_ms=(time.time()-t0)*1000)
  messages=[]
  if system_prompt:messages.append({"role":"system","content":system_prompt})
  messages.append({"role":"user","content":prompt})
  payload={"model":model_id,"messages":messages,"max_tokens":max_tokens,"temperature":temperature,"stream":False}
  if tools:payload["tools"]=tools
  req=request.Request(f"{self.base_url}/chat/completions",data=json.dumps(payload).encode(),headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json","User-Agent":"aftergraph-study012-agent/1.0"},method="POST")
  try:
   with request.urlopen(req,timeout=60) as resp:data=json.loads(resp.read().decode())
   msg=((data.get("choices") or [{}])[0].get("message") or {})
   usage=data.get("usage") or {};pt=int(usage.get("prompt_tokens") or 0);ct=int(usage.get("completion_tokens") or 0)
   self.operational_status="LIVE_VERIFIED"
   raw={"gateway":"huggingface","backend":"groq","provider_response":data}
   return ProviderResponse(content=msg.get("content") or "",tool_calls=msg.get("tool_calls") or [],prompt_tokens=pt,completion_tokens=ct,total_tokens=int(usage.get("total_tokens") or pt+ct),cost_usd=float(usage.get("cost") or 0.0),latency_ms=(time.time()-t0)*1000,provider="hf_groq",model_id=model_id,is_live=True,raw_response=raw)
  except Exception as exc:
   return ProviderResponse(content="",provider="hf_groq",model_id=model_id,is_live=False,latency_ms=(time.time()-t0)*1000,raw_response={"gateway":"huggingface","backend":"groq","failure":provider_error_snapshot(exc,self.api_key)})
