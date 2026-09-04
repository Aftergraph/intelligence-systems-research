from adapters.base import BaseRuntimeAdapter

# ponytail: AutoGen / Multi-Agent GroupChat Adapter (Phase E).
# Translates Mission contract into an AutoGen multi-agent conversation configuration.
# Maps verification into a dedicated Critic/Verifier agent prompt.

class AutoGenAdapter(BaseRuntimeAdapter):
    def __init__(self):
        super().__init__("autogen_runtime")

    def compile_mission(self, mission_doc):
        """Translates Mission contract into AutoGen agent configuration."""
        obj = mission_doc["objective"]["outcome"]
        criteria = mission_doc.get("success", {}).get("all", [])
        retry_limit = mission_doc.get("recovery", {}).get("retry_limit", 0)

        config = {
            "agents": [
                {
                    "name": "ExecutorAgent",
                    "system_message": f"You execute tools to achieve: {obj}. Constraints: {mission_doc.get('constraints', {})}.",
                    "capabilities": ["mcp_tools"]
                },
                {
                    "name": "VerifierAgent",
                    "system_message": f"You independently verify evidence for criteria: {criteria}. Terminate only when satisfied.",
                    "is_critic": True
                },
                {
                    "name": "UserProxy",
                    "human_input_mode": "NEVER",
                    "max_consecutive_auto_reply": retry_limit + 5
                }
            ],
            "group_chat": {
                "max_round": 15,
                "speaker_selection_method": "auto"
            },
            "termination_criteria": {
                "required_criteria": criteria,
                "objective": obj,
                "budget_tokens": mission_doc.get("budget", {}).get("tokens", {}).get("max"),
                "recovery_limit": retry_limit
            }
        }
        return config

    def extract_semantic_invariants(self, compiled_config):
        term = compiled_config["termination_criteria"]
        return {
            "objective": term["objective"],
            "criteria": sorted(term["required_criteria"]),
            "budget_tokens": term["budget_tokens"],
            "recovery_limit": term["recovery_limit"]
        }
