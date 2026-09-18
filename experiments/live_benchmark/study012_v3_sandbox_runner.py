"""STUDY-012 v3 Novita Sandbox execution controller.

Sandbox executes NVIDIA task + observational judge calls. Local controller
performs deterministic evaluation and pinned Sentinel DI verification, then
appends canonical observations and checkpoint evidence.
"""
from __future__ import annotations
import hashlib,json,os,time
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from experiments.live_benchmark.study012_matrix_plan_v3 import allocation
from experiments.live_benchmark.study012_evaluators import deterministic_exact,parse_judge_observation,canonicalize
from experiments.live_benchmark.study012_sentinel_adapter import verify_checkout,verify_research_envelope

ROOT=Path(__file__).resolve().parents[2]
EXECUTION_ID="study012-cross-model-v3-20260918"
JUDGE_MODEL="nvidia/nemotron-3-super-120b-a12b"
BATCH_SIZE=20
MAX_ATTEMPTS=2
NVIDIA_URL="https://integrate.api.nvidia.com/v1/chat/completions"

WORKER=r'''
import argparse,json,os,time,urllib.request,urllib.error
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
NVIDIA_URL="https://integrate.api.nvidia.com/v1/chat/completions"
JUDGE_MODEL="nvidia/nemotron-3-super-120b-a12b"
MAX_ATTEMPTS=2
RETRY={408,429,500,502,503,504}

def call(model,prompt,max_tokens):
    key=os.environ["NVIDIA_API_KEY"]
    last=None
    for attempt in range(1,MAX_ATTEMPTS+1):
        payload={"model":model,"messages":[{"role":"user","content":prompt}],"max_tokens":max_tokens,"temperature":0.0,"stream":False}
        if model in {"nvidia/nemotron-3-ultra-550b-a55b","nvidia/nemotron-3-super-120b-a12b"}:
            payload["reasoning_effort"]="none"
        req=urllib.request.Request(NVIDIA_URL,data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json","User-Agent":"aftergraph-study012-v3-sandbox/1.0"},method="POST")
        started=time.time()
        try:
            with urllib.request.urlopen(req,timeout=75) as resp:
                data=json.loads(resp.read().decode())
            msg=((data.get("choices") or [{}])[0].get("message") or {})
            usage=data.get("usage") or {}
            return {"is_live":True,"content":msg.get("content") or "","prompt_tokens":int(usage.get("prompt_tokens") or 0),"completion_tokens":int(usage.get("completion_tokens") or 0),"total_tokens":int(usage.get("total_tokens") or 0),"attempts":attempt,"latency_ms":(time.time()-started)*1000,"failure":None}
        except urllib.error.HTTPError as e:
            body=e.read(4096).decode("utf-8","replace")
            failure={"category":"HTTP_ERROR","http_status":e.code,"reason":str(e.reason),"body":body[:500]}
            last={"is_live":False,"content":"","prompt_tokens":0,"completion_tokens":0,"total_tokens":0,"attempts":attempt,"latency_ms":(time.time()-started)*1000,"failure":failure}
            if e.code not in RETRY or attempt>=MAX_ATTEMPTS:return last
            time.sleep(attempt)
        except Exception as e:
            last={"is_live":False,"content":"","prompt_tokens":0,"completion_tokens":0,"total_tokens":0,"attempts":attempt,"latency_ms":(time.time()-started)*1000,"failure":{"category":type(e).__name__,"reason":str(e)[:300]}}
            if attempt>=MAX_ATTEMPTS:return last
            time.sleep(attempt)
    return last

def judge_prompt(expected,candidate):
    return "You are an observational evaluator. Return exactly VERIFIED if CANDIDATE equals EXPECTED after trimming whitespace; FAILED if not; ABSTAIN if malformed.\nEXPECTED: "+expected+"\nCANDIDATE: "+candidate

ap=argparse.ArgumentParser()
ap.add_argument("--plan",required=True);ap.add_argument("--workloads",required=True);ap.add_argument("--checkpoint",required=True);ap.add_argument("--out",required=True);ap.add_argument("--limit",type=int,default=20)
args=ap.parse_args()
plan=json.loads(Path(args.plan).read_text());workloads={w["r2_class"]:w for w in json.loads(Path(args.workloads).read_text())["workloads"]}
done=set()
cp=Path(args.checkpoint)
if cp.exists():
    for line in cp.read_text().splitlines():
        if line.strip():done.add(json.loads(line)["trace_id"])
pending=[r for r in plan["rows"] if r["trace_id"] not in done][:args.limit]
def process_row(row):
    w=workloads[row["r2_class"]]
    task=call(row["model_id"],w["prompt"],256)
    judge=None
    if row["condition"] in {"J","JD"} and task and task["is_live"]:
        judge=call(JUDGE_MODEL,judge_prompt(w["response_contract"]["expected"],task["content"]),32)
    return {"row":row,"workload_id":w["id"],"task":task,"judge":judge}

out=[]
with ThreadPoolExecutor(max_workers=2) as pool:
    futures={pool.submit(process_row,row):row for row in pending}
    for future in as_completed(futures):
        rec=future.result()
        out.append(rec)
        with cp.open("a",encoding="utf-8") as fh:fh.write(json.dumps({"trace_id":rec["row"]["trace_id"]},sort_keys=True,separators=(",",":"))+"\n")
Path(args.out).write_text(json.dumps(out,sort_keys=True,separators=(",",":")))
print(json.dumps({"processed":len(out),"checkpoint_rows":len(done)+len(out)}))
'''

def sha_text(s:str)->str:return hashlib.sha256((s or "").encode()).hexdigest()
def canonical_hash(obj:Any)->str:return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def load_workloads():
 obj=json.loads((ROOT/"data/study012_r2_extension_v03.json").read_text(encoding="utf-8"));return {w["r2_class"]:w for w in obj["workloads"]}

def sentinel_envelope(row,w,response_text):
 body={"responseText":response_text,"responseSha256":sha_text(response_text),"provider":"nvidia","modelId":row["model_id"]}
 criterion=w["response_contract"]
 return {"schema":"aftergraph.research-evidence/1.0","subject":{"studyId":"STUDY-012","executionId":EXECUTION_ID,"traceId":row["trace_id"],"workloadId":w["id"],"condition":row["condition"],"executorRef":"novita-sandbox:study012-v3","missionId":"research:"+row["trace_id"]},"evidence":{"body":body,"digestSha256":canonical_hash(body),"observedAt":datetime.now(timezone.utc).isoformat().replace("+00:00","Z")},"criterion":{**criterion,"acceptanceCriteriaHash":canonical_hash(criterion)}}

def finalize(raw,w,sentinel_dir):
 row=raw["row"];task=raw["task"];judge_raw=raw.get("judge");txt=task.get("content","") if task else ""
 det=deterministic_exact(txt,w) if row["condition"] in {"D","JD","DI"} and task and task.get("is_live") else None
 judge=None
 if row["condition"] in {"J","JD"} and judge_raw:
  judge=parse_judge_observation(judge_raw.get("content","") if judge_raw.get("is_live") else "ABSTAIN")
  judge.update({"is_live":bool(judge_raw.get("is_live")),"response_text":judge_raw.get("content",""),"response_hash":sha_text(judge_raw.get("content","")),"failure_provenance":judge_raw.get("failure")})
 sentinel=None;ind=None
 if row["condition"]=="DI" and task and task.get("is_live"):
  sentinel=verify_research_envelope(sentinel_dir,sentinel_envelope(row,w,txt))
  rec=sentinel.get("receipt") if isinstance(sentinel,dict) else None
  if rec:ind={"result":"passed" if sentinel.get("verdict")=="VERIFIED" else "failed","verifier_id":rec.get("verifierRef"),"evidence_ref":rec.get("receiptId"),"verified_at":rec.get("verifiedAt")}
 canonical=canonicalize(row["condition"],deterministic=det,judge=judge,independent_receipt=ind)
 return {**row,"study_id":"STUDY-012","execution_id":EXECUTION_ID,"pooling_with_prior_runs":False,"source_workload_id":w["id"],"workload_hash":canonical_hash(w),"execution_class":"LIVE_VALID" if task and task.get("is_live") else "LIVE_PROVIDER_FAILURE","response_text":txt,"response_hash":sha_text(txt),"task":task,"deterministic":det,"judge":judge,"sentinel":sentinel,"independent_receipt":ind,"canonical":canonical}

def run(out_dir:Path,sentinel_dir:Path,novita_key:str,nvidia_key:str):
 if novita_key:
  os.environ["NOVITA_API_KEY"]=novita_key
 from novita_sandbox.code_interpreter import Sandbox
 ok,reason=verify_checkout(sentinel_dir)
 if not ok:return {"decision":"BLOCKED","reason":reason}
 plan={"schema_version":"aftergraph.study012.v3-sandbox-plan.v0.1","execution_id":EXECUTION_ID,"rows":allocation()}
 workloads_doc=json.loads((ROOT/"data/study012_r2_extension_v03.json").read_text(encoding="utf-8"))
 out_dir.mkdir(parents=True,exist_ok=True);obs=out_dir/"observations.jsonl";cp_local=out_dir/"checkpoint.jsonl"
 done=set()
 if obs.exists():
  for line in obs.read_text(encoding="utf-8").splitlines():
   if line.strip():done.add(json.loads(line)["trace_id"])
 checkpoint_text=""
 workloads=load_workloads();sandbox_count=0;sb=None
 def rebuild_checkpoint():
  ordered=[r["trace_id"] for r in plan["rows"] if r["trace_id"] in done]
  return "".join(json.dumps({"trace_id":t},sort_keys=True,separators=(",",":"))+"\n" for t in ordered)
 try:
  while len(done)<960:
   checkpoint_text=rebuild_checkpoint()
   if sb is None:
    sb=Sandbox.create(timeout=3600,metadata={"study_id":"STUDY-012","execution_id":EXECUTION_ID,"purpose":"v3-live-runner"},envs={"NVIDIA_API_KEY":nvidia_key},auto_pause=True)
    sandbox_count+=1
    wd="/workspace/study012";sb.files.make_dir(wd);sb.files.write(wd+"/worker.py",WORKER);sb.files.write(wd+"/plan.json",json.dumps(plan,separators=(",",":")));sb.files.write(wd+"/workloads.json",json.dumps(workloads_doc,separators=(",",":")))
   if checkpoint_text:sb.files.write(wd+"/checkpoint.jsonl",checkpoint_text)
   elif sb.files.exists(wd+"/checkpoint.jsonl"):sb.files.remove(wd+"/checkpoint.jsonl")
   try:
    sb.commands.run(f"python {wd}/worker.py --plan {wd}/plan.json --workloads {wd}/workloads.json --checkpoint {wd}/checkpoint.jsonl --out {wd}/batch.json --limit {BATCH_SIZE}",timeout=900)
    raw=json.loads(sb.files.read(wd+"/batch.json"))
   except Exception:
    try: sb.kill()
    except Exception: pass
    sb=None
    continue
   for rr in raw:
    tr=rr["row"]["trace_id"]
    if tr in done:continue
    final=finalize(rr,workloads[rr["row"]["r2_class"]],sentinel_dir)
    with obs.open("a",encoding="utf-8",newline="\n") as fh:fh.write(json.dumps(final,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n")
    done.add(tr)
   checkpoint_text=rebuild_checkpoint()
   cp_local.write_text(checkpoint_text,encoding="utf-8")
 finally:
  if sb is not None:
   try:sb.kill()
   except Exception:pass
 summary={"decision":"COMPLETED" if len(done)==960 else "PARTIAL","observations":len(done),"unique_traces":len(done),"sandboxes_created":sandbox_count}
 (out_dir/"RUN-SUMMARY.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 return summary
