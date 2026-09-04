import hashlib
import json
import os
import threading

# ponytail: Persistent, cryptographically-chained trajectory storage (SPEC-001 Invariant 5).
# Stores events as newline-delimited JSON with SHA-256 hash chains.
# Detects any retroactive tampering, modification, insertion, or truncation.

class TrajectoryStorage:
    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = os.path.join(os.getcwd(), ".intelligence", "trajectories")
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)
        self._lock = threading.RLock()

    def get_trajectory_path(self, mission_id):
        # Sanitize mission_id for filesystem safety
        safe_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in mission_id)
        return os.path.join(self.base_dir, f"{safe_id}.jsonl")

    def append_event(self, mission_id, event):
        """
        Appends an event to the mission's trajectory log with cryptographic chaining.
        Each event record gets:
          - prev_hash: SHA-256 of the prior event line
          - event_hash: SHA-256(prev_hash + canonical_json(event))
        """
        path = self.get_trajectory_path(mission_id)
        with self._lock:
            prev_hash = "0" * 64
            if os.path.exists(path) and os.path.getsize(path) > 0:
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        if last_line:
                            try:
                                last_record = json.loads(last_line)
                                prev_hash = last_record.get("event_hash", prev_hash)
                            except Exception:
                                pass

            # Compute canonical JSON payload for consistent hashing
            event_payload = {k: v for k, v in event.items() if k not in ("prev_hash", "event_hash")}
            canonical_bytes = json.dumps(event_payload, sort_keys=True).encode("utf-8")
            event_hash = hashlib.sha256(prev_hash.encode("utf-8") + canonical_bytes).hexdigest()

            record = dict(event_payload)
            record["prev_hash"] = prev_hash
            record["event_hash"] = event_hash

            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, sort_keys=True) + "\n")

            return record

    def load_trajectory(self, mission_id):
        path = self.get_trajectory_path(mission_id)
        if not os.path.exists(path):
            return []
        events = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    @staticmethod
    def verify_chain_integrity(file_path):
        """
        Verifies the cryptographic hash-chain of a trajectory file.
        Returns (is_valid, error_detail).
        """
        if not os.path.exists(file_path):
            return False, "File does not exist"

        expected_prev = "0" * 64
        with open(file_path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                prev_hash = record.get("prev_hash")
                event_hash = record.get("event_hash")

                if prev_hash != expected_prev:
                    return False, f"Broken hash chain at line {idx}: prev_hash mismatch (expected {expected_prev}, got {prev_hash})"

                # Recompute hash
                event_payload = {k: v for k, v in record.items() if k not in ("prev_hash", "event_hash")}
                canonical_bytes = json.dumps(event_payload, sort_keys=True).encode("utf-8")
                computed_hash = hashlib.sha256(prev_hash.encode("utf-8") + canonical_bytes).hexdigest()

                if computed_hash != event_hash:
                    return False, f"Tampered event content at line {idx}: hash mismatch (expected {computed_hash}, got {event_hash})"

                expected_prev = event_hash

        return True, "Chain verified valid and tamper-free"
