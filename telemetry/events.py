import hashlib
import json
import time
from typing import Any, Dict, List, Optional

# ponytail: Hash-Chained Trajectory Ledger (RFC-conformant hash chain, not a Merkle Tree).
# Guarantees forward tamper-evidence. Full history rewrites are detected via external signed anchors.

class TrajectoryRecorder:
    def __init__(self, mission_id: str, genesis_hash: Optional[str] = None):
        self.mission_id = mission_id
        self.events: List[Dict[str, Any]] = []
        self.current_hash = genesis_hash or hashlib.sha256(mission_id.encode("utf-8")).hexdigest()
        self._anchors: Dict[int, str] = {}  # sequence -> signed anchor hash

    def emit_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        canonical_str = json.dumps(payload, sort_keys=True)
        prev_hash = self.current_hash

        event_bytes = f"{prev_hash}:{ts}:{event_type}:{canonical_str}".encode("utf-8")
        event_hash = hashlib.sha256(event_bytes).hexdigest()

        event_doc = {
            "seq": len(self.events) + 1,
            "timestamp": ts,
            "event_type": event_type,
            "payload": payload,
            "prev_hash": prev_hash,
            "event_hash": event_hash
        }
        self.events.append(event_doc)
        self.current_hash = event_hash
        return event_doc

    def record_external_anchor(self, sequence: int, anchor_hash: str):
        self._anchors[sequence] = anchor_hash

    def verify_integrity(self) -> bool:
        """Recalculates hash chain from genesis; verifies anchors if present."""
        is_valid, _ = self.audit_integrity()
        return is_valid

    def audit_integrity(self) -> tuple[bool, Optional[str]]:
        """Audits the trajectory specifically for mutation, deletion, reordering, or anchor mismatch."""
        if not self.events:
            return True, None

        expected_seq = 1
        running_hash = self.events[0]["prev_hash"]

        for idx, e in enumerate(self.events):
            # 1. Check sequence ordering & deletion
            if e["seq"] != expected_seq:
                return False, f"Sequence discontinuity at index {idx}: expected {expected_seq}, found {e['seq']}"
            expected_seq += 1

            # 2. Check hash chaining continuity
            if e["prev_hash"] != running_hash:
                return False, f"Broken hash chain at seq {e['seq']}: prev_hash does not match preceding event"

            # 3. Recalculate event hash (detect payload mutation)
            canonical_str = json.dumps(e["payload"], sort_keys=True)
            expected_bytes = f"{e['prev_hash']}:{e['timestamp']}:{e['event_type']}:{canonical_str}".encode("utf-8")
            computed_hash = hashlib.sha256(expected_bytes).hexdigest()
            if e["event_hash"] != computed_hash:
                return False, f"Event payload mutation detected at seq {e['seq']}"

            # 4. Check external anchor match if one was pinned
            if e["seq"] in self._anchors:
                if self._anchors[e["seq"]] != computed_hash:
                    return False, f"External anchor mismatch at seq {e['seq']}: expected {self._anchors[e['seq']]}"

            running_hash = e["event_hash"]

        return True, None
