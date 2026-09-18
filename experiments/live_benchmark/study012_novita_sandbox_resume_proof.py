"""Two-sandbox checkpoint/restore proof for Novita execution fabric."""
from __future__ import annotations
import json
from experiments.live_benchmark.study012_novita_sandbox_fabric import NovitaSandboxFabric,build_plan
from experiments.live_benchmark.study012_matrix_plan_v2 import allocation

def run_proof(sample_size:int=12, first_phase:int=5):
    plan=build_plan(allocation()[:sample_size])
    fabric=NovitaSandboxFabric()
    sb1=fabric.create(purpose="checkpoint-proof-phase-1",timeout=300)
    try:
        fabric.seed(sb1,plan)
        p1=fabric.run_checkpoint_phase(sb1,limit=first_phase)
    finally:
        fabric.kill(sb1)

    sb2=fabric.create(purpose="checkpoint-proof-phase-2",timeout=300)
    try:
        fabric.seed(sb2,plan,p1.checkpoint_text)
        p2=fabric.run_checkpoint_phase(sb2,limit=0)
    finally:
        fabric.kill(sb2)

    rows=[json.loads(x) for x in p2.checkpoint_text.splitlines() if x.strip()]
    return {
      "schema_version":"aftergraph.study012.sandbox-resume-proof.v0.1",
      "plan_rows":sample_size,
      "phase1_checkpoint_rows":len([x for x in p1.checkpoint_text.splitlines() if x.strip()]),
      "phase2_checkpoint_rows":len(rows),
      "unique_trace_ids":len({x["trace_id"] for x in rows}),
      "phase1_sandbox_id":p1.sandbox_id,
      "phase2_sandbox_id":p2.sandbox_id,
      "different_sandboxes":p1.sandbox_id!=p2.sandbox_id,
      "complete":len(rows)==sample_size and len({x["trace_id"] for x in rows})==sample_size,
    }

if __name__=="__main__":
    print(json.dumps(run_proof(),indent=2,sort_keys=True))
