import json,subprocess
from pathlib import Path
from experiments.live_benchmark.study012_full_runner import load_fixtures,preflight,judge_prompt,canonical_hash
from experiments.live_benchmark.study012_matrix_plan import allocation

def test_full_runner_has_exact_one_fixture_per_r2_class():
 f=load_fixtures()
 assert set(f)=={r["r2_class"] for r in allocation()}
 assert len(f)==8
 assert all(w["response_contract"]["format"]=="EXACT_TOKEN" for w in f.values())

def test_judge_prompt_is_observational_and_enum_bounded():
 w=next(iter(load_fixtures().values()))
 p=judge_prompt(w,"x")
 assert "observational evaluator" in p
 assert "VERIFIED" in p and "FAILED" in p and "ABSTAIN" in p

def test_preflight_rejects_wrong_sentinel_checkout(tmp_path):
 (tmp_path/"bin").mkdir(); (tmp_path/"bin"/"sentinel-research-verify.js").write_text("")
 r=preflight(tmp_path)
 assert r["decision"]=="BLOCKED"
 assert r["network_calls_performed"]==0
