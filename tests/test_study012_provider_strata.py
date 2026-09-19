import json
from pathlib import Path
from providers.stratum_resolver import execution_plan, validate_independence
ROOT=Path(__file__).resolve().parents[1]

def test_study012_has_two_independent_ready_strata():
    m=json.loads((ROOT/"data/study012_provider_model_matrix.json").read_text())
    ok,reasons=validate_independence(m)
    assert ok, reasons
    p=execution_plan(m)
    assert p["decision"]=="READY_FOR_OWNER_GATE"
    assert {s["provider"] for s in p["strata"]}=={"openrouter","google"}

def test_same_gateway_cannot_fake_independence():
    m={"model_strata":[
      {"id":"a","provider":"x","endpoint":"https://same","readiness":"READY","models":[{"exact_model_id":"m1"}]},
      {"id":"b","provider":"y","endpoint":"https://same","readiness":"READY","models":[{"exact_model_id":"m2"}]},
    ]}
    ok,reasons=validate_independence(m)
    assert not ok and "endpoint_not_distinct" in reasons
