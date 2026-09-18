from experiments.live_benchmark.study012_live_runner import run_canary

def test_canary_cannot_call_without_owner_gate(tmp_path):
 r=run_canary(owner_approval_ref=None,provider_name="google",model_id="gemini-2.5-flash",prompt="ping",out_dir=tmp_path)
 assert r["decision"]=="BLOCKED"
 assert r["network_call_attempted"] is False

def test_canary_rejects_unfrozen_model_before_network(tmp_path):
 r=run_canary(owner_approval_ref="OWNER-TEST",provider_name="google",model_id="not-frozen",prompt="ping",out_dir=tmp_path)
 assert r["decision"]=="BLOCKED"
 assert r["network_call_attempted"] is False
 assert r["reason"]=="provider_model_not_frozen"
