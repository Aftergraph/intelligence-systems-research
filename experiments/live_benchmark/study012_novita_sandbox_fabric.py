"""Novita Sandbox execution fabric for STUDY-012 recovery-v2.

This module manages isolated execution sandboxes and explicit checkpoint export/
restore. Provider credentials are NOT injected by default.
"""
from __future__ import annotations
import hashlib,json,os,tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

NOVITA_SDK_VERSION="2.1.1"
WORKDIR="/workspace/study012"

def canonical_hash(obj:Any)->str:
    raw=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

WORKER_SCRIPT=r"""
import argparse,json,hashlib
from pathlib import Path

ap=argparse.ArgumentParser()
ap.add_argument("--plan",required=True)
ap.add_argument("--checkpoint",required=True)
ap.add_argument("--limit",type=int,default=0)
args=ap.parse_args()

plan=json.loads(Path(args.plan).read_text())
cp=Path(args.checkpoint)
done=set()
if cp.exists():
    for line in cp.read_text().splitlines():
        if line.strip():
            done.add(json.loads(line)["trace_id"])

pending=[x for x in plan["rows"] if x["trace_id"] not in done]
if args.limit>0:
    pending=pending[:args.limit]

cp.parent.mkdir(parents=True,exist_ok=True)
for row in pending:
    rec={
      "trace_id":row["trace_id"],
      "row_hash":hashlib.sha256(json.dumps(row,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
      "status":"SANDBOX_EXECUTION_CHECKPOINT_PROOF"
    }
    with cp.open("a",encoding="utf-8") as fh:
        fh.write(json.dumps(rec,sort_keys=True,separators=(",",":"))+"\n")

rows=[json.loads(x) for x in cp.read_text().splitlines() if x.strip()] if cp.exists() else []
print(json.dumps({
  "processed_now":len(pending),
  "checkpoint_rows":len(rows),
  "unique_trace_ids":len({x["trace_id"] for x in rows})
}))
"""

@dataclass
class SandboxResult:
    sandbox_id:str
    stdout:str
    checkpoint_text:str

class NovitaSandboxFabric:
    def __init__(self, api_key:str|None=None):
        if api_key:
            os.environ["NOVITA_API_KEY"]=api_key

    def _sdk(self):
        from novita_sandbox.code_interpreter import Sandbox
        return Sandbox

    def create(self, *, purpose:str, timeout:int=3600):
        Sandbox=self._sdk()
        return Sandbox.create(
            timeout=timeout,
            metadata={"study_id":"STUDY-012","execution_id":"study012-recovery-v2-20260918","purpose":purpose},
            auto_pause=True,
        )

    def seed(self, sandbox, plan:dict[str,Any], checkpoint_text:str|None=None)->None:
        sandbox.files.make_dir(WORKDIR)
        sandbox.files.write(f"{WORKDIR}/worker.py",WORKER_SCRIPT)
        sandbox.files.write(f"{WORKDIR}/plan.json",json.dumps(plan,sort_keys=True,separators=(",",":")))
        if checkpoint_text:
            sandbox.files.write(f"{WORKDIR}/checkpoint.jsonl",checkpoint_text)

    def run_checkpoint_phase(self, sandbox, *, limit:int=0)->SandboxResult:
        cmd=f"python {WORKDIR}/worker.py --plan {WORKDIR}/plan.json --checkpoint {WORKDIR}/checkpoint.jsonl --limit {int(limit)}"
        out=sandbox.commands.run(cmd,timeout=300)
        checkpoint=sandbox.files.read(f"{WORKDIR}/checkpoint.jsonl")
        sid=getattr(sandbox,"sandbox_id",None) or getattr(sandbox,"id","")
        return SandboxResult(str(sid),getattr(out,"stdout",str(out)),checkpoint)

    def kill(self,sandbox)->None:
        sandbox.kill()

def build_plan(rows:list[dict[str,Any]])->dict[str,Any]:
    return {
      "schema_version":"aftergraph.study012.sandbox-plan.v0.1",
      "execution_id":"study012-recovery-v2-20260918",
      "rows":rows,
      "rows_hash":canonical_hash(rows),
    }
