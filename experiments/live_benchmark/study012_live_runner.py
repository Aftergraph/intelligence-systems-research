"""STUDY-012 gated live runner wiring.

No live call can occur unless an explicit owner approval reference is supplied
and zero-inference preflight returns READY_TO_EXECUTE.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any
from experiments.live_benchmark.study012_preflight import evaluate as preflight
from experiments.live_benchmark.study012_execution import ReceiptJournal, Checkpoint
from providers.openrouter import OpenRouterProvider
from providers.google import GoogleProvider

ROOT=Path(__file__).resolve().parents[2]

def _provider(name:str):
    if name=="openrouter": return OpenRouterProvider()
    if name=="google": return GoogleProvider()
    raise ValueError(f"unsupported_provider:{name}")

def _hash_text(text:str)->str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def classify_canary(response, expected_output:str|None)->str:
    if not response.is_live:
        return "LIVE_PROVIDER_FAILURE"
    if expected_output is not None and (response.content or "").strip() != expected_output.strip():
        return "LIVE_SEMANTIC_FAILURE"
    return "LIVE_VALID"

def run_canary(*, owner_approval_ref:str|None, provider_name:str, model_id:str, prompt:str, out_dir:str|Path, expected_output:str|None=None)->dict[str,Any]:
    gate=preflight(owner_approval_ref=owner_approval_ref)
    if gate["decision"]!="READY_TO_EXECUTE":
        return {"decision":"BLOCKED","gate":gate,"network_call_attempted":False}
    matrix=json.loads((ROOT/"data/study012_provider_model_matrix.json").read_text(encoding="utf-8"))
    allowed={(s["provider"],m["exact_model_id"]) for s in matrix["model_strata"] if s.get("readiness")=="READY" for m in s["models"]}
    if (provider_name,model_id) not in allowed:
        return {"decision":"BLOCKED","reason":"provider_model_not_frozen","network_call_attempted":False}
    provider=_provider(provider_name)
    response=provider.generate(prompt,model=model_id,max_tokens=32,temperature=0.0,dry_run=False)
    execution_class=classify_canary(response,expected_output)
    receipt={
      "run_id":"study012-canary-v1",
      "trace_id":f"canary-{provider_name}-{model_id}",
      "condition":"D",
      "provider":provider_name,
      "model_id":model_id,
      "execution_class":execution_class,
      "request_hash":_hash_text(prompt),
      "response_hash":_hash_text(response.content or json.dumps(response.raw_response or {},sort_keys=True)),
      "expected_output_hash":_hash_text(expected_output) if expected_output is not None else None,
      "is_live":bool(response.is_live),
      "prompt_tokens":response.prompt_tokens,
      "completion_tokens":response.completion_tokens,
      "total_tokens":response.total_tokens,
      "latency_ms":response.latency_ms,
      "cost_usd":response.cost_usd,
    }
    out=Path(out_dir)
    journal=ReceiptJournal(out/"receipts.jsonl")
    checkpoint=Checkpoint(out/"checkpoint.jsonl")
    rh=journal.append(receipt); checkpoint.record(receipt["trace_id"],rh)
    return {"decision":"COMPLETED","network_call_attempted":True,"receipt_hash":rh,"execution_class":execution_class,"is_live":response.is_live}
