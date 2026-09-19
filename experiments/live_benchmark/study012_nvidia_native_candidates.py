"""Probe NVIDIA-native lightweight models for STUDY-012 recovery."""
from __future__ import annotations
import hashlib,json
from providers.nvidia import NvidiaProvider
TARGETS=[
 "nvidia/nemotron-3.5-lightning-30b-a3b",
 "nvidia/nemotron-nano-3-30b-a3b",
 "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
]
PROMPT="Return exactly READY_OK and nothing else.";EXPECTED="READY_OK"
def run():
 rows=[]
 for model in TARGETS:
  for i in range(1,3):
   r=NvidiaProvider().generate(PROMPT,model=model,max_tokens=32,temperature=0.0,dry_run=False)
   rows.append({"model_id":model,"index":i,"is_live":bool(r.is_live),"semantic_match":bool(r.is_live and (r.content or "").strip()==EXPECTED),"content_sha256":hashlib.sha256((r.content or "").encode()).hexdigest(),"latency_ms":r.latency_ms,"failure":(r.raw_response or {}).get("failure") if not r.is_live else None})
 summary={}
 for model in TARGETS:
  s=[r for r in rows if r["model_id"]==model]
  summary[model]={"calls":2,"live":sum(r["is_live"] for r in s),"semantic_match":sum(r["semantic_match"] for r in s),"failures":[r["failure"] for r in s if r["failure"]]}
 return {"schema_version":"aftergraph.study012.nvidia-native-candidates.v0.1","rows":rows,"summary":summary}
if __name__=="__main__":print(json.dumps(run(),indent=2,sort_keys=True))
