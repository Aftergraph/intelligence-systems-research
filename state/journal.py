import hashlib
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

# ponytail: Append-Only Structured Event Journal.
# Canonical ground-truth for the Durable Work Plane.
# Every state mutation and capability effect is committed here BEFORE returning to models.

class EventJournal:
    def __init__(self, mission_id: str, journal_path: Optional[str] = None):
        self.mission_id = mission_id
        if journal_path:
            self.journal_path = journal_path
        else:
            j_dir = os.path.join(os.getcwd(), ".intelligence", "journal")
            os.makedirs(j_dir, exist_ok=True)
            self.journal_path = os.path.join(j_dir, f"journal_{mission_id}.jsonl")

        self._sequence = 0
        self._last_event_id: Optional[str] = None
        self._events: List[Dict[str, Any]] = []
        self._load_existing()

    def _load_existing(self):
        if os.path.exists(self.journal_path):
            with open(self.journal_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        evt = json.loads(line)
                        self._events.append(evt)
                        self._sequence = evt.get("sequence", self._sequence)
                        self._last_event_id = evt.get("event_id")

    def append_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        actor_principal: str = "AgentPrincipal",
        run_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Appends a cryptographically hashed, sequenced event to the journal."""
        self._sequence += 1
        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        event = {
            "event_id": event_id,
            "mission_id": self.mission_id,
            "run_id": run_id or f"run-{self.mission_id[:8]}",
            "sequence": self._sequence,
            "timestamp": ts,
            "actor_principal": actor_principal,
            "causal_parent": self._last_event_id,
            "correlation_id": correlation_id or event_id,
            "event_type": event_type,
            "payload": payload,
            "payload_hash": payload_hash
        }

        # Write to disk immediately (atomic append)
        with open(self.journal_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")

        self._events.append(event)
        self._last_event_id = event_id
        return event

    def list_events(self) -> List[Dict[str, Any]]:
        return list(self._events)

    def get_latest_sequence(self) -> int:
        return self._sequence
