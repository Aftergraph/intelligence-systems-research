from experiments.live_benchmark.study012_matrix_plan_v2 import allocation,summary
from experiments.live_benchmark.study012_recovery_v2_readiness import TARGETS

def test_v2_matrix_is_exact_and_separate():
 rows=allocation(); s=summary(rows)
 assert len(rows)==960 and len({r["trace_id"] for r in rows})==960
 assert all(r["trace_id"].startswith("S12V2-") for r in rows)
 assert s["by_provider"]=={"google":480,"nvidia":480}
 assert s["classes"]==8 and s["conditions"]==4 and s["replicates_per_class_condition"]==30

def test_v2_readiness_is_exactly_nine_calls():
 assert len(TARGETS)==3
 assert {x[1] for x in TARGETS}=={"gemini-2.5-flash","nvidia/nemotron-3-ultra-550b-a55b","nvidia/nemotron-3-super-120b-a12b"}
