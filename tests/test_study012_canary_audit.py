import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_canary_audit_matches_frozen_expected_hash():
 a=json.loads((ROOT/"data/study012_runs/canary-20260918/CANARY-AUDIT.json").read_text())
 assert a["expected_output_sha256"]=="ef6f2c4edbeace425f20c92bf38017723cd48d583f2b6a80dc674043f49ce3e5"
 by={x["provider"]:x for x in a["attempts"]}
 assert by["openrouter"]["audited_execution_class"]=="LIVE_VALID"
 assert by["google"]["audited_execution_class"]=="LIVE_SEMANTIC_FAILURE"
 assert a["scope_exhausted"] is True
 assert a["additional_live_calls_authorized"] is False
