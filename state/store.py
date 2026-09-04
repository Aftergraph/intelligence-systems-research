from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import copy
import json
import os
import time

@dataclass
class MissionStateData:
    mission_id: str
    lifecycle_state: str = "DRAFT"
    criteria_status: Dict[str, str] = field(default_factory=dict)
    budget_spent: Dict[str, Any] = field(default_factory=lambda: {"tokens": 0, "usd": 0.0, "actions": 0})
    recovery_attempts_remaining: int = 3

@dataclass
class WorldStateData:
    environment_variables: Dict[str, str] = field(default_factory=dict)
    workspace_path: str = ""
    modified_files: List[str] = field(default_factory=list)
    git_commit_sha: Optional[str] = None

@dataclass
class AgentStateData:
    step_index: int = 0
    active_model: str = ""
    active_provider: str = ""
    pending_tool_call: Optional[Dict[str, Any]] = None
    last_candidate_completion: Optional[str] = None

class DurableStateStore:
    def __init__(self, mission_id: str, storage_dir: Optional[str] = None):
        self.mission_id = mission_id
        self.storage_dir = storage_dir or os.path.join(os.getcwd(), ".intelligence", "state")
        os.makedirs(self.storage_dir, exist_ok=True)

        self.mission_state = MissionStateData(mission_id=mission_id)
        self.world_state = WorldStateData(workspace_path=os.getcwd())
        self.agent_state = AgentStateData()

    def snapshot(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "timestamp": time.time(),
            "mission_state": copy.deepcopy(self.mission_state.__dict__),
            "world_state": copy.deepcopy(self.world_state.__dict__),
            "agent_state": copy.deepcopy(self.agent_state.__dict__)
        }

    def persist(self, sequence: int = 0) -> str:
        data = self.snapshot()
        filepath = os.path.join(self.storage_dir, f"state_{self.mission_id}_{sequence:05d}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return filepath

    def restore_from_snapshot(self, snapshot_data: Dict[str, Any]):
        self.mission_id = snapshot_data["mission_id"]
        self.mission_state = MissionStateData(**snapshot_data["mission_state"])
        self.world_state = WorldStateData(**snapshot_data["world_state"])
        self.agent_state = AgentStateData(**snapshot_data["agent_state"])

    def materialize_from_events(self, events: List[Dict[str, Any]]):
        """Materializes in-memory state by replaying append-only journal events."""
        for evt in events:
            etype = evt.get("event_type")
            payload = evt.get("payload", {})
            if etype == "mission.created":
                self.mission_state.lifecycle_state = "READY"
            elif etype == "mission.authorized":
                self.mission_state.lifecycle_state = "AUTHORIZED"
            elif etype == "mission.started":
                self.mission_state.lifecycle_state = "RUNNING"
            elif etype == "state.changed":
                new_st = payload.get("new_state")
                if new_st:
                    self.mission_state.lifecycle_state = new_st
            elif etype == "budget.committed":
                toks = payload.get("tokens", 0)
                usd = payload.get("cost_usd", 0.0)
                self.mission_state.budget_spent["tokens"] += toks
                self.mission_state.budget_spent["usd"] += usd
                self.mission_state.budget_spent["actions"] += 1
            elif etype == "capability.completed":
                f_mod = payload.get("modified_file")
                if f_mod and f_mod not in self.world_state.modified_files:
                    self.world_state.modified_files.append(f_mod)
            elif etype == "candidate_completion.created":
                self.agent_state.last_candidate_completion = payload.get("completion")
                self.mission_state.lifecycle_state = "VERIFYING"
            elif etype == "verification.passed":
                self.mission_state.lifecycle_state = "VERIFIED"
            elif etype == "verification.failed":
                self.mission_state.lifecycle_state = "RECOVERING"
                self.mission_state.recovery_attempts_remaining = max(0, self.mission_state.recovery_attempts_remaining - 1)
