import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_recovery_registry_keeps_execution_and_inference_readiness_separate():
 r=json.loads((ROOT/"data/study012_provider_recovery_registry_v01.json").read_text())
 assert r["execution_fabric"]["selected"]=="novita_sandbox"
 assert r["execution_fabric"]["status"]=="READY"
 assert r["execution_fabric"]["resume_proof"]["complete"] is True
 ready=[x for x in r["routes"] if x["role"]=="task" and x["status"].startswith("READY")]
 assert ready==[]
 assert "No second independent task inference route is READY" in r["current_scientific_blocker"]

def test_blocked_routes_are_explicit_and_no_silent_substitution_allowed():
 r=json.loads((ROOT/"data/study012_provider_recovery_registry_v01.json").read_text())
 by={x["route"]:x["status"] for x in r["routes"]}
 assert by["google_gemini_developer_api"]=="BLOCKED_QUOTA"
 assert by["openrouter_paid"]=="BLOCKED_BALANCE"
 assert by["novita_model_api"]=="BLOCKED_BALANCE"
 assert by["zai_direct"]=="BLOCKED_BALANCE"
 assert by["byteplus_ark"]=="BLOCKED_MODEL_NOT_OPEN"
 assert by["opencode_go"]=="BLOCKED_BALANCE"
 assert by["huggingface_router_groq"]=="BLOCKED_AUTH"
 assert by["opencode_zen_mimo_free"]=="BLOCKED_CLIENT_POLICY"
 assert "Never silently substitute a blocked route." in r["selection_rules"]
