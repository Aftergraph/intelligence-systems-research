from adapters.base import BaseRuntimeAdapter
from runtime.engine import MissionEngine

class NativeRuntimeAdapter(BaseRuntimeAdapter):
    def __init__(self):
        super().__init__("native_reference_runtime")

    def compile_mission(self, mission_doc):
        engine = MissionEngine()
        engine.load_mission(mission_doc)
        return engine

    def extract_semantic_invariants(self, compiled_engine):
        m = compiled_engine.mission
        return {
            "objective": m["objective"]["outcome"],
            "criteria": sorted(m.get("success", {}).get("all", [])),
            "budget_tokens": m.get("budget", {}).get("tokens", {}).get("max"),
            "recovery_limit": m.get("recovery", {}).get("retry_limit", 0)
        }
