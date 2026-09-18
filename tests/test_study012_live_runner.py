from experiments.live_benchmark.study012_live_runner import run_canary, classify_canary
from providers.base import ProviderResponse

def test_canary_cannot_call_without_owner_gate(tmp_path):
 r=run_canary(owner_approval_ref=None,provider_name="google",model_id="gemini-2.5-flash",prompt="ping",out_dir=tmp_path)
 assert r["decision"]=="BLOCKED"
 assert r["network_call_attempted"] is False

def test_canary_rejects_unfrozen_model_before_network(tmp_path):
 r=run_canary(owner_approval_ref="OWNER-TEST",provider_name="google",model_id="not-frozen",prompt="ping",out_dir=tmp_path)
 assert r["decision"]=="BLOCKED"
 assert r["network_call_attempted"] is False
 assert r["reason"]=="provider_model_not_frozen"

def test_semantic_success_required_for_live_valid():
 ok=ProviderResponse(content="AFTERGRAPH_CANARY_OK",provider="x",model_id="m",is_live=True)
 wrong=ProviderResponse(content="",provider="x",model_id="m",is_live=True)
 down=ProviderResponse(content="",provider="x",model_id="m",is_live=False)
 assert classify_canary(ok,"AFTERGRAPH_CANARY_OK")=="LIVE_VALID"
 assert classify_canary(wrong,"AFTERGRAPH_CANARY_OK")=="LIVE_SEMANTIC_FAILURE"
 assert classify_canary(down,"AFTERGRAPH_CANARY_OK")=="LIVE_PROVIDER_FAILURE"
