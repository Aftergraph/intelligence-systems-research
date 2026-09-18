"""Bounded STUDY-012 provider failure forensics probe."""
from __future__ import annotations
import hashlib,json,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from providers.google import GoogleProvider
from providers.openrouter import OpenRouterProvider

TARGETS=[
 ("google","gemini-2.5-flash","Return exactly FORENSIC_OK and nothing else.","FORENSIC_OK"),
 ("openrouter","google/gemma-4-31b-it","Return exactly FORENSIC_OK and nothing else.","FORENSIC_OK"),
 ("openrouter","z-ai/glm-5.2","Return exactly VERIFIED and nothing else.","VERIFIED"),
]
MAX_CALLS=12

def _provider(name:str):
    return GoogleProvider() if name=="google" else OpenRouterProvider()

def _one(provider_name:str,model_id:str,prompt:str,expected:str,phase:str,index:int)->dict[str,Any]:
    r=_provider(provider_name).generate(prompt,model=model_id,max_tokens=16,temperature=0.0,dry_run=False)
    return {
      "provider":provider_name,"model_id":model_id,"phase":phase,"index":index,
      "is_live":bool(r.is_live),"semantic_match":bool(r.is_live and (r.content or "").strip()==expected),
      "content_sha256":hashlib.sha256((r.content or "").encode()).hexdigest(),
      "prompt_tokens":r.prompt_tokens,"completion_tokens":r.completion_tokens,
      "total_tokens":r.total_tokens,"cost_usd":r.cost_usd,"latency_ms":r.latency_ms,
      "failure":(r.raw_response or {}).get("failure") if not r.is_live else None,
    }

def run()->dict[str,Any]:
    rows=[]
    for provider_name,model_id,prompt,expected in TARGETS:
        rows.append(_one(provider_name,model_id,prompt,expected,"sequential",1))
        with ThreadPoolExecutor(max_workers=3) as pool:
            fut=[pool.submit(_one,provider_name,model_id,prompt,expected,"burst3",i) for i in range(1,4)]
            rows.extend(f.result() for f in fut)
    if len(rows)!=MAX_CALLS: raise RuntimeError("probe_call_count_mismatch")
    summary={}
    for provider_name,model_id,_,_ in TARGETS:
        subset=[r for r in rows if r["provider"]==provider_name and r["model_id"]==model_id]
        summary[f"{provider_name}:{model_id}"]={
          "calls":len(subset),
          "live":sum(r["is_live"] for r in subset),
          "semantic_match":sum(r["semantic_match"] for r in subset),
          "sequential_live":sum(r["is_live"] for r in subset if r["phase"]=="sequential"),
          "burst_live":sum(r["is_live"] for r in subset if r["phase"]=="burst3"),
          "failure_categories":{},
          "http_statuses":{},
        }
        s=summary[f"{provider_name}:{model_id}"]
        for r in subset:
            f=r.get("failure") or {}
            if f:
                cat=str(f.get("category")); s["failure_categories"][cat]=s["failure_categories"].get(cat,0)+1
                status=str(f.get("http_status")); s["http_statuses"][status]=s["http_statuses"].get(status,0)+1
    return {"schema_version":"aftergraph.study012.provider-forensics.v0.1","calls":len(rows),"rows":rows,"summary":summary}

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
