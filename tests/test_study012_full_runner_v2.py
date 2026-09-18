import json
from pathlib import Path
from experiments.live_benchmark.study012_full_runner_v2 import preflight,load_fixtures,prior_accounting,EXECUTION_ID
from experiments.live_benchmark.study012_matrix_plan_v2 import allocation

def test_v2_runner_identity_and_fixture_coverage():
 assert EXECUTION_ID=="study012-recovery-v2-20260918"
 assert len(load_fixtures())==8
 assert len(allocation())==960
 assert all(r["trace_id"].startswith("S12V2-") for r in allocation())

def test_resume_accounting_counts_prior_attempts_and_costs():
 rows=[{"task_attempts":2,"judge_attempts":1,"task_cost_usd":0.01,"judge_cost_usd":0.02},{"task_attempts":1,"judge_attempts":0,"task_cost_usd":0.03}]
 calls,cost=prior_accounting(rows)
 assert calls==4
 assert abs(cost-0.06)<1e-12

def test_v2_preflight_fails_closed_on_wrong_sentinel(tmp_path):
 (tmp_path/"bin").mkdir();(tmp_path/"bin"/"sentinel-research-verify.js").write_text("")
 r=preflight(tmp_path)
 assert r["decision"]=="BLOCKED" and r["network_calls_performed"]==0
