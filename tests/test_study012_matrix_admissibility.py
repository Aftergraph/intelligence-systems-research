from experiments.live_benchmark.study012_matrix_plan import allocation, summary
from experiments.live_benchmark.study012_admissibility import evaluate

def test_matrix_plan_is_exact_balanced_and_deterministic():
    a=allocation(); b=allocation()
    assert a==b
    s=summary(a)
    assert s["observations"]==960
    assert s["by_provider"]=={"openrouter":480,"google":480}
    assert s["classes"]==8 and s["conditions"]==4
    assert s["replicates_per_class_condition"]==30
    assert len({x["trace_id"] for x in a})==960
    assert all(x["result_partition"].startswith("full-matrix/") for x in a)

def test_admissibility_has_only_real_external_verifier_transport_blocker():
    r=evaluate()
    assert r["decision"]=="NOT_ADMISSIBLE"
    assert r["network_calls_performed"]==0
    assert r["reasons"]==["sentinel_transport_not_bound"]
    assert r["incomplete_extension_workloads"]==[]
    assert r["retry_policy"]["max_total_api_calls"]==2880
    assert r["hard_cost_stop_usd"]==4.0
