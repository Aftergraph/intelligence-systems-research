from scripts.study012_v3_freeze import build,verify
def test_v3_freeze_is_ready_but_not_authorized():
 m=build()
 assert len(m["files"])>=18
 assert m["gates"]["readiness_decision"]=="READY"
 assert m["gates"]["readiness_observations"]==9
 assert m["gates"]["sandbox_resume_complete"] is True
 assert m["gates"]["sandbox_resume_different_sandboxes"] is True
 assert m["gates"]["provider_independence_claim_allowed"] is False
 assert m["gates"]["pooling_with_prior_runs"] is False
 assert m["gates"]["full_run_owner_approval_required"] is True
 assert verify(m)
def test_v3_freeze_detects_drift():
 m=build();k=next(iter(m["files"]));m["files"][k]="0"*64
 assert not verify(m)
