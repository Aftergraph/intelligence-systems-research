import json
from typing import Any, Dict, List, Optional

# ponytail: Progressive Disclosure Prompt Compiler.
# Produces sub-250 token Tier 1 prompt views to prevent instruction interference on 8B-14B models.

class PromptCompiler:
    def __init__(self):
        pass

    def compile_tier1_prompt(
        self,
        mission_id: str,
        objective: str,
        constraints: List[str],
        criteria_ids: List[str],
        allowed_capabilities: List[str],
        budget_remaining: Dict[str, Any],
        diagnostic_feedback: Optional[str] = None
    ) -> str:
        lines = [
            f"[MISSION_ID]: {mission_id}",
            f"[OBJECTIVE]: {objective}",
            f"[ACTIVE_CONSTRAINTS]: {'; '.join(constraints) if constraints else 'None'}",
            f"[REQUIRED_CRITERIA_IDS]: {', '.join(criteria_ids)}",
            f"[PERMITTED_CAPABILITIES]: {', '.join(allowed_capabilities)}",
            f"[REMAINING_BUDGET]: tokens={budget_remaining.get('tokens', 'unlimited')}, usd=${budget_remaining.get('usd', 0.0):.2f}"
        ]
        if diagnostic_feedback:
            lines.append(f"[ASSURANCE_DIAGNOSTIC_FEEDBACK]: {diagnostic_feedback}")

        lines.append("[INSTRUCTION]: Solve the objective using permitted capabilities. When finished, emit your candidate solution.")
        return "\n".join(lines)
