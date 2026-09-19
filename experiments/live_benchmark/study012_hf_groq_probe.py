"""Bounded Hugging Face router -> Groq recovery probe."""
from __future__ import annotations
import hashlib,json
from providers.hf_groq import HFGroqProvider
MODEL="openai/gpt-oss-120b:groq"
PROMPT="Return exactly HF_GROQ_READY_OK and nothing else."
EXPECTED="HF_GROQ_READY_OK"
def _one(index):
 r=HFGroqProvider().generate(PROMPT,model=MODEL,max_tokens=32,temperature=0.0,dry_run=False)
 return {"index":index,"gateway":"huggingface","backend":"groq","is_live":bool(r.is_live),"semantic_match":bool(r.is_live and (r.content or "").strip()==EXPECTED),"content_sha256":hashlib.sha256((r.content or "").encode()).hexdigest(),"prompt_tokens":r.prompt_tokens,"completion_tokens":r.completion_tokens,"total_tokens":r.total_tokens,"cost_usd":r.cost_usd,"latency_ms":r.latency_ms,"failure":(r.raw_response or {}).get("failure") if not r.is_live else None}
def run():
 rows=[_one(i) for i in range(1,4)]
 return {"schema_version":"aftergraph.study012.hf-groq-probe.v0.1","model_id":MODEL,"gateway":"huggingface","backend":"groq","rows":rows,"summary":{"calls":3,"live":sum(r["is_live"] for r in rows),"semantic_match":sum(r["semantic_match"] for r in rows),"failures":[r["failure"] for r in rows if r["failure"]]}}
if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
