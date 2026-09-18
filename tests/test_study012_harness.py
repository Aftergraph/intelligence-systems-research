from experiments.live_benchmark.run_study_012 import dry_run
from experiments.live_benchmark.study012_analyze import analyze
def test_dry_run_is_synthetic_and_preserves_frozen_workloads():
 rows=dry_run(); assert len(rows)==48
 assert {r["execution_class"] for r in rows}=={"DRY_RUN"}
 assert {r["condition"] for r in rows}=={"J","D","JD","DI"}
 assert len({r["source_workload_id"] for r in rows})==12
def test_analysis_is_conservative_for_available_r2_mapping():
 a=analyze(dry_run())
 assert a["applicable_classes"]==2 and a["covered_classes"]==2
 assert a["deterministically_verified"]==0 and a["independently_verified"]==0
def test_judge_cannot_override_oracle():
 rows=dry_run(); r=next(x for x in rows if x["condition"]=="JD")
 r["judge_verdict"]="VERIFIED"; r["oracle_verdict"]="FAILED"
 a=analyze(rows)
 assert a["judge_oracle_disagreements"]==1
 assert a["deterministically_verified"]==0
