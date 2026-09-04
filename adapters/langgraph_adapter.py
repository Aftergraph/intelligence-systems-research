from adapters.base import BaseRuntimeAdapter

# ponytail: LangGraph / StateGraph Adapter (Phase E).
# Translates Mission contract into an executable DAG state graph specification.
# Without requiring heavy LangGraph dependencies, models its exact node & edge topology.

class LangGraphAdapter(BaseRuntimeAdapter):
    def __init__(self):
        super().__init__("langgraph_runtime")

    def compile_mission(self, mission_doc):
        """Translates Mission contract into a LangGraph StateGraph topology."""
        obj = mission_doc["objective"]["outcome"]
        criteria = mission_doc.get("success", {}).get("all", [])
        retry_limit = mission_doc.get("recovery", {}).get("retry_limit", 0)

        graph_def = {
            "state_schema": {
                "mission_id": mission_doc["metadata"]["id"],
                "objective": obj,
                "current_step": "init",
                "trajectory": [],
                "evidence": {},
                "retry_count": 0,
                "is_verified": False
            },
            "nodes": {
                "planner": f"Plan actions to achieve: {obj}",
                "executor": "Execute requested tool actions via MCP",
                "verifier": f"Independently evaluate evidence against criteria: {criteria}",
                "recovery": f"Handle failure retry (max {retry_limit})"
            },
            "edges": [
                ("__start__", "planner"),
                ("planner", "executor"),
                ("executor", "verifier"),
            ],
            "conditional_edges": {
                "verifier": {
                    "condition": "all_criteria_satisfied",
                    "branches": {
                        "True": "__end__",
                        "False": "recovery"
                    }
                },
                "recovery": {
                    "condition": f"retry_count < {retry_limit}",
                    "branches": {
                        "True": "planner",
                        "False": "__end__"
                    }
                }
            },
            "metadata": {
                "budget_tokens": mission_doc.get("budget", {}).get("tokens", {}).get("max"),
                "recovery_limit": retry_limit
            }
        }
        return graph_def

    def extract_semantic_invariants(self, compiled_graph):
        schema = compiled_graph["state_schema"]
        meta = compiled_graph["metadata"]
        # Extract criteria from verifier node
        verifier_str = compiled_graph["nodes"]["verifier"]
        crit_part = verifier_str.split("criteria: ")[1]
        criteria = eval(crit_part)  # parse stringified list safely

        return {
            "objective": schema["objective"],
            "criteria": sorted(criteria),
            "budget_tokens": meta["budget_tokens"],
            "recovery_limit": meta["recovery_limit"]
        }
