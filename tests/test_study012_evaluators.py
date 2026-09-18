from experiments.live_benchmark.study012_evaluators import deterministic_exact,parse_judge_observation,canonicalize,validate_independent_receipt

W={"oracle":"effect_count_equals_one","response_contract":{"expected":"NO_SECOND_EFFECT"}}

def test_exact_deterministic_evaluator():
 assert deterministic_exact("NO_SECOND_EFFECT",W)["verdict"]=="VERIFIED"
 assert deterministic_exact("maybe",W)["verdict"]=="FAILED"

def test_judge_only_never_canonical_verified():
 j=parse_judge_observation("VERIFIED")
 assert canonicalize("J",judge=j)["canonical_verdict"]=="UNESTABLISHED"

def test_jd_deterministic_controls_disagreement():
 d={"verdict":"FAILED"}; j={"verdict":"VERIFIED"}
 r=canonicalize("JD",deterministic=d,judge=j)
 assert r["canonical_verdict"]=="FAILED"
 assert r["judge_verdict"]=="VERIFIED"

def test_di_requires_valid_sentinel_receipt():
 d={"verdict":"VERIFIED"}
 assert canonicalize("DI",deterministic=d)["canonical_verdict"]=="BLOCKED"
 receipt={"verifier_id":"sentinel:domain-verifier","result":"passed","evidence_ref":"dvr_abc"}
 assert canonicalize("DI",deterministic=d,independent_receipt=receipt)["canonical_verdict"]=="VERIFIED"
 bad={"verifier_id":"self","result":"passed","evidence_ref":"dvr_abc"}
 assert validate_independent_receipt(bad)[0] is False
