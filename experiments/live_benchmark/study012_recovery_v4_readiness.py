"""Final nine-call readiness gate for STUDY-012 recovery v4."""
from __future__ import annotations
import hashlib,json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from providers.ollama_local import OllamaLocalProvider
from providers.nvidia import NvidiaProvider

TARGETS=[
    ("ollama-local","qwen3.6:latest","Return exactly LOCAL_V4_OK and nothing else.","LOCAL_V4_OK"),
    ("nvidia","nvidia/nemotron-3-ultra-550b-a55b","Return exactly NVIDIA_V4_OK and nothing else.","NVIDIA_V4_OK"),
    ("nvidia","nvidia/nemotron-3-super-120b-a12b","Return exactly VERIFIED and nothing else.","VERIFIED"),
]

def _provider(name:str):
    return OllamaLocalProvider() if name=="ollama-local" else NvidiaProvider()

def _one(provider_name:str,model:str,prompt:str,expected:str,phase:str,index:int)->dict[str,Any]:
    r=_provider(provider_name).generate(prompt,model=model,max_tokens=32,temperature=0.0,dry_run=False)
    content=(r.content or "").strip()
    failure=None
    if not r.is_live:
        raw=r.raw_response or {}
        failure=raw.get("failure") if isinstance(raw,dict) else None
    return {
      "provider":provider_name,
      "model_id":model,
      "phase":phase,
      "index":index,
      "is_live":bool(r.is_live),
      "semantic_match":bool(r.is_live and content==expected),
      "content_sha256":hashlib.sha256((r.content or "").encode()).hexdigest(),
      "prompt_tokens":r.prompt_tokens,
      "completion_tokens":r.completion_tokens,
      "total_tokens":r.total_tokens,
      "latency_ms":r.latency_ms,
      "cost_usd":r.cost_usd,
      "failure":failure,
    }

def run()->dict[str,Any]:
    rows=[]
    for provider_name,model,prompt,expected in TARGETS:
        rows.append(_one(provider_name,model,prompt,expected,"sequential",1))
        with ThreadPoolExecutor(max_workers=2) as pool:
            fut=[pool.submit(_one,provider_name,model,prompt,expected,"burst2",i) for i in range(1,3)]
            rows.extend(f.result() for f in fut)
    summary={}
    for provider_name,model,_,_ in TARGETS:
        subset=[r for r in rows if r["provider"]==provider_name and r["model_id"]==model]
        summary[f"{provider_name}:{model}"]={
          "calls":len(subset),
          "live":sum(r["is_live"] for r in subset),
          "semantic_match":sum(r["semantic_match"] for r in subset),
          "failures":[r["failure"] for r in subset if r["failure"]],
        }
    ready=len(rows)==9 and all(r["is_live"] and r["semantic_match"] for r in rows)
    return {
      "schema_version":"aftergraph.study012.recovery-v4-readiness.v0.1",
      "execution_id":"study012-recovery-v4-20260918",
      "decision":"READY" if ready else "BLOCKED",
      "calls":len(rows),
      "rows":rows,
      "summary":summary,
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
