from experiments.live_benchmark.study012_matrix_plan_v4 import allocation,summary

def test_v4_matrix_is_exact_balanced_and_unique():
 rows=allocation(); s=summary(rows)
 assert s["observations"]==960
 assert s["unique_trace_ids"]==960
 assert s["by_provider"]=={"ollama-local":480,"nvidia":480}
 assert s["classes"]==8
 assert s["conditions"]==4
 assert s["replicates_per_class_condition"]==30
 assert all(r["trace_id"].startswith("S12V4-") for r in rows)

def test_v4_alternates_frozen_strata_without_substitution():
 rows=allocation()
 assert {r["provider"] for r in rows}=={"ollama-local","nvidia"}
 assert {r["model_id"] for r in rows}=={"qwen3.6:latest","nvidia/nemotron-3-ultra-550b-a55b"}
