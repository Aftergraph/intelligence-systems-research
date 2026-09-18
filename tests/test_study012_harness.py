from experiments.live_benchmark.run_study_012 import dry_run
from experiments.live_benchmark.study012_analyze import analyze
def test_dry_run_composes_parent_and_amendment():
 rows=dry_run(); assert len(rows)==72
 assert len({r["source_workload_id"] for r in rows})==18
 assert {r["condition"] for r in rows}=={"J","D","JD","DI"}
def test_r2_surface_is_complete_8_of_8():
 a=analyze(dry_run())
 assert a["applicable_classes"]==8 and a["covered_classes"]==8
 assert a["deterministically_verified"]==0 and a["independently_verified"]==0
def test_judge_cannot_override_oracle():
 rows=dry_run(); r=next(x for x in rows if x["condition"]=="JD")
 r["judge_verdict"]="VERIFIED"; r["oracle_verdict"]="FAILED"
 a=analyze(rows)
 assert a["judge_oracle_disagreements"]==1
 assert a["deterministically_verified"]==0
