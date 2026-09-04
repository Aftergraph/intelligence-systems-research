import hashlib
import json
import os
import time
from typing import Any, Callable, Dict, List, Optional

# ponytail: Hardened Checkpoint Manager with External Effect Reconciliation.
# Uses idempotency keys to ensure side effects are not duplicated on crash/restart.

class CheckpointManager:
    def __init__(self, checkpoints_dir: Optional[str] = None):
        self.checkpoints_dir = checkpoints_dir or os.path.join(os.getcwd(), ".intelligence", "checkpoints")
        os.makedirs(self.checkpoints_dir, exist_ok=True)
        self._external_receipts: Dict[str, Dict[str, Any]] = {}

    def record_external_receipt(self, idempotency_key: str, receipt: Dict[str, Any]):
        self._external_receipts[idempotency_key] = receipt

    def get_external_receipt(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        return self._external_receipts.get(idempotency_key)

    def save_checkpoint(
        self,
        mission_id: str,
        sequence: int,
        payload: Dict[str, Any],
        pending_operations: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        data = {
            "state": payload,
            "external_receipts": self._external_receipts,
            "pending_operations": pending_operations or []
        }
        payload_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
        payload_sha256 = hashlib.sha256(payload_bytes).hexdigest()

        checkpoint_doc = {
            "mission_id": mission_id,
            "sequence": sequence,
            "timestamp": time.time(),
            "payload_sha256": payload_sha256,
            "data": data
        }

        filename = f"checkpoint_{mission_id}_{sequence:05d}.json"
        filepath = os.path.join(self.checkpoints_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(checkpoint_doc, f, indent=2)
        return filepath

    def load_latest_checkpoint(self, mission_id: str) -> Optional[Dict[str, Any]]:
        candidates = [
            f for f in os.listdir(self.checkpoints_dir)
            if f.startswith(f"checkpoint_{mission_id}_") and f.endswith(".json")
        ]
        if not candidates:
            return None

        candidates.sort()
        latest_file = os.path.join(self.checkpoints_dir, candidates[-1])
        with open(latest_file, "r", encoding="utf-8") as f:
            doc = json.load(f)

        # Integrity verification
        data_bytes = json.dumps(doc["data"], sort_keys=True).encode("utf-8")
        computed_sha = hashlib.sha256(data_bytes).hexdigest()
        if computed_sha != doc["payload_sha256"]:
            raise ValueError(f"Corrupted checkpoint detected in {latest_file}")

        data = doc["data"]
        # Restore external receipts cache if present
        if "external_receipts" in data:
            self._external_receipts.update(data["external_receipts"])

        # Backward compatibility for flat payload
        if "state" in data:
            return data["state"]
        return data

    def reconcile_external_effects(
        self,
        mission_id: str,
        external_verifier_fn: Callable[[str], bool]
    ) -> Dict[str, str]:
        """Queries external environment to reconcile uncertain operations without duplicating side effects."""
        reconciled = {}
        for key, receipt in list(self._external_receipts.items()):
            if receipt.get("status") == "UNCERTAIN_CRASH":
                already_done = external_verifier_fn(key)
                if already_done:
                    receipt["status"] = "COMMITTED_RECONCILED"
                    reconciled[key] = "RECONCILED_SUCCESS"
                else:
                    receipt["status"] = "RETRY_REQUIRED"
                    reconciled[key] = "RECONCILED_RETRY"
        return reconciled
