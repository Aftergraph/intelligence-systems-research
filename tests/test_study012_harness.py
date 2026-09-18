from experiments.live_benchmark.run_study_012 import dry_run
from experiments.live_benchmark.study012_analyze import analyze
def test_dry_run_is_synthetic_and_complete():
 rows=dry_run(); assert len(rows)==32
 assert {r["execution_class"] for r in rows}=={"DRY_RUN"}
 assert {r["condition"] for r in rows}=={"J","D","JD","DI"}
def test_analysis_covers_all_r2_classes_without_claiming_success():
 a=analyze(dry_run())
 assert a["applicable_classes"]==8 and a["covered_classes"]==8
 assert a["deterministically_verified"]==0
 assert a["independently_verified"]==0
def test_judge_cannot_override_oracle():
 rows=dry_run()
 r=next(x for x in rows if x["condition"]=="JD")
 r["judge_verdict"]="VERIFIED"; r["oracle_verdict"]="FAILED"
 a=analyze(rows)
 assert a["judge_oracle_disagreements"]==1
 assert a["deterministically_verified"]==0
