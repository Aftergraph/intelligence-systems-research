import os
import sys
import jsonschema
import json

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from prototype.compiler import MissionCompiler
from prototype.progressive import ProgressiveDisclosure
from prototype.dashboard import MissionDashboard
from runtime.engine import MissionEngine

def test_prototype_flow():
    # 1. Test Natural Language to Mission Compilation
    compiler = MissionCompiler()
    nl_intent = "Refactor database connection pool, run unit tests, and verify performance under $12 budget."
    compiled_mission = compiler.compile(nl_intent, mission_id="mission-db-refactor")

    # Validate compiled mission against JSON Schema
    with open(os.path.join(workspace, "schemas", "mission.v0alpha1.json"), "r", encoding="utf-8") as f:
        schema = json.load(f)
    jsonschema.validate(instance=compiled_mission, schema=schema)
    assert compiled_mission["budget"]["money"]["max"] == 12.0
    assert "unit_tests_passed" in compiled_mission["success"]["all"]
    print("SUCCESS: Intent compilation to valid schema verified.")

    # 2. Test Progressive Disclosure
    t1_payload = ProgressiveDisclosure.get_tier1_execution_payload(compiled_mission)
    t1_tokens = len(t1_payload) / 3.8
    assert t1_tokens <= 250, f"Tier 1 context payload too large: {t1_tokens} tokens"
    print(f"SUCCESS: Tier 1 progressive disclosure verified at {t1_tokens:.1f} tokens (<= 250 budget).")

    # 3. Test Dashboard & Needs You alert in Engine
    engine = MissionEngine()
    engine.load_mission(compiled_mission)
    dashboard = MissionDashboard(engine)

    # Initial view
    view = dashboard.render_view()
    assert "mission-db-refactor" in view
    assert "READY" in view

    # Authorize & Start
    delegation = {
        "id": "del-db-01",
        "principal": "urn:principal:human:jonas",
        "delegate": "urn:agent:db-agent",
        "purpose": "urn:mission:mission-db-refactor:v1",
        "scope": {"allowed_capabilities": ["mcp://*"]},
        "valid_from": "2026-09-01T00:00:00Z",
        "expires_at": "2026-12-31T23:59:59Z"
    }
    engine.authorize(delegation)
    engine.start()

    # Test Human Pause
    dashboard.user_pause()
    view_paused = dashboard.render_view()
    assert "PAUSED" in view_paused
    assert "NEEDS YOU" in view_paused

    # Test Human Resume
    dashboard.user_resume()
    assert engine.state == "RUNNING"

    # Test Human Takeover
    dashboard.user_takeover(reason="Testing human takeover")
    assert engine.budget_spent["human_interventions"] == 1
    assert engine.state == "PAUSED"

    print("SUCCESS: Phase C human-first dashboard and exception interaction verified.")

if __name__ == "__main__":
    test_prototype_flow()
