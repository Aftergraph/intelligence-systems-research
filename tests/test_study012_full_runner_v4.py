import json
from pathlib import Path
from experiments.live_benchmark.study012_full_runner_v4 import preflight,load_fixtures,prior_accounting,EXECUTION_ID
from experiments.live_benchmark.study012_matrix_plan_v4 import allocation

def test_v4_runner_identity_and_fixture_coverage():
 assert EXECUTION_ID=="study012-recovery-v4-20260918"
 assert len(load_fixtures())==8
 assert len(allocation())==960
 assert all(r["trace_id"].startswith("S12V4-") for r in allocation())

def test_v4_resume_accounting_counts_prior_attempts_and_costs():
 rows=[{"task_attempts":2,"judge_attempts":1,"task_cost_usd":0.0,"judge_cost_usd":0.0},
       {"task_attempts":1,"judge_attempts":0,"task_cost_usd":0.0}]
 calls,cost=prior_accounting(rows)
 assert calls==4
 assert cost==0.0

def test_v4_preflight_is_blocked_before_explicit_owner_grant(tmp_path):
 (tmp_path/"bin").mkdir()
 (tmp_path/"bin"/"sentinel-research-verify.js").write_text("")
 r=preflight(tmp_path)
 assert r["decision"]=="BLOCKED"
 assert r["network_calls_performed"]==0
 assert "owner_approval_not_granted" in r["reasons"]
