from experiments.live_benchmark.study012_matrix_plan_v3 import allocation,summary
from experiments.live_benchmark.study012_v3_readiness import TARGETS,MAX_ATTEMPTS

def test_v3_plan_is_exact_960_and_cross_model_not_cross_provider():
 rows=allocation();s=summary(rows)
 assert len(rows)==960 and len({r["trace_id"] for r in rows})==960
 assert all(r["trace_id"].startswith("S12V3-") for r in rows)
 assert len(s["by_model"])==2
 assert set(r["provider"] for r in rows)=={"nvidia"}

def test_v3_readiness_surface_is_three_distinct_models():
 models={m for _,m,_,_ in TARGETS}
 assert len(models)==3
 assert MAX_ATTEMPTS==2
