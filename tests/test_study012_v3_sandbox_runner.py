from experiments.live_benchmark.study012_v3_sandbox_runner import load_workloads,canonical_hash,EXECUTION_ID
from experiments.live_benchmark.study012_matrix_plan_v3 import allocation

def test_v3_runner_identity_and_coverage():
 assert EXECUTION_ID=="study012-cross-model-v3-20260918"
 assert len(load_workloads())==8
 rows=allocation()
 assert len(rows)==960 and len({r["trace_id"] for r in rows})==960
 assert all(r["trace_id"].startswith("S12V3-") for r in rows)

def test_v3_runner_never_claims_provider_independence():
 models={r["model_id"] for r in allocation()}
 assert models=={"nvidia/nemotron-3-ultra-550b-a55b","nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"}
 assert {r["provider"] for r in allocation()}=={"nvidia"}
