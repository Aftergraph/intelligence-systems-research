import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_google_retry_canary_is_exact_semantic_match():
    a=json.loads((ROOT/"data/study012_runs/canary-google-retry-20260918/GOOGLE-RETRY-AUDIT.json").read_text())
    assert a["audited_execution_class"]=="LIVE_VALID"
    assert a["expected_output_sha256"]==a["observed_response_sha256"]
    assert a["configuration"]["thinking_budget"]==0
    assert a["scope_exhausted"] is True
    assert a["additional_live_calls_authorized"] is False
