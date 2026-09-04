from typing import Any, Dict, List, Optional

# ponytail: Hardened Context Manager with Segregated Pinned Control Context.
# Separates PINNED CONTROL CONTEXT (reconstructed from canonical state) from COMPRESSIBLE WORK CONTEXT.
# Even under extreme conversation volume or heavy tool outputs, hard constraints are 100% invariant.

class ContextManager:
    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self._pinned_control_context: Dict[str, Any] = {}
        self._pinned_system_prompt: str = ""
        self._pinned_constraints: List[str] = []
        self._compressible_turns: List[Dict[str, Any]] = []

    def set_pinned_control_context(
        self,
        mission_id: str,
        objective: str,
        constraints: List[str],
        criteria_ids: List[str],
        remaining_budget: Dict[str, Any],
        lifecycle_state: str = "RUNNING"
    ):
        """Pins canonical mission control boundaries."""
        self._pinned_constraints = list(constraints)
        self._pinned_control_context = {
            "mission_id": mission_id,
            "objective": objective,
            "constraints": list(constraints),
            "criteria_ids": list(criteria_ids),
            "remaining_budget": dict(remaining_budget),
            "lifecycle_state": lifecycle_state
        }
        # Formulate pinned system header
        lines = [
            f"[CANONICAL_MISSION_ID]: {mission_id}",
            f"[OBJECTIVE]: {objective}",
            f"[HARD_CONSTRAINTS]: {'; '.join(constraints) if constraints else 'None'}",
            f"[REQUIRED_CRITERIA]: {', '.join(criteria_ids)}",
            f"[BUDGET]: {remaining_budget}",
            f"[LIFECYCLE_STATE]: {lifecycle_state}"
        ]
        self._pinned_system_prompt = "\n".join(lines)

    def set_pinned_context(self, system_prompt: str, constraints: List[str]):
        """Backward compatibility."""
        self._pinned_system_prompt = system_prompt
        self._pinned_constraints = list(constraints)

    def add_turn(self, role: str, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None):
        self._compressible_turns.append({
            "role": role,
            "content": content,
            "tool_calls": tool_calls or []
        })
        if len(self._compressible_turns) > self.max_turns:
            # Compress by shedding oldest non-pinned dialogue turns
            self._compressible_turns = self._compressible_turns[-self.max_turns:]

    def add_observation(self, capability_uri: str, observation: Any):
        obs_str = str(observation)
        # If tool output is massive, compress work context safely
        if len(obs_str) > 1000:
            obs_str = obs_str[:500] + f"\n... [Truncated {len(obs_str) - 500} bytes of intermediate tool data] ..."
        self.add_turn(role="tool", content=f"[{capability_uri} Observation]: {obs_str}")

    def get_assembled_context(self) -> List[Dict[str, Any]]:
        # Always inject pinned control context as immutable system message
        messages = [{"role": "system", "content": self._pinned_system_prompt}]
        messages.extend(self._compressible_turns)
        return messages

    def get_preserved_constraints(self) -> List[str]:
        return list(self._pinned_constraints)
