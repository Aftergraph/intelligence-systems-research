from experiments.live_benchmark.study012_works_verification_bridge import validate_receipt,build_request,VERIFIER_HEADER

GOOD={"result":"passed","verifier_id":"sentinel:domain-verifier","evidence_ref":"dvr_"+"a"*64,"verified_at":"2026-09-18T17:00:00Z"}

def test_bridge_matches_canonical_works_contract():
 ok,reason=validate_receipt(GOOD); assert ok and reason is None
 req=build_request("https://works.example","wrk_1","x"*32,GOOD)
 assert req.full_url=="https://works.example/v1/works/wrk_1/verification"
 assert req.get_header("X-works-verifier-token")=="x"*32

def test_bridge_rejects_self_and_bad_dvr():
 bad=dict(GOOD,verifier_id="agent:self")
 assert validate_receipt(bad)[0] is False
 bad=dict(GOOD,evidence_ref="receipt_abc")
 assert validate_receipt(bad)[0] is False

def test_bridge_requires_dedicated_long_token():
 import pytest
 with pytest.raises(ValueError,match="verifier_token_too_short"):
  build_request("https://works.example","wrk_1","short",GOOD)
