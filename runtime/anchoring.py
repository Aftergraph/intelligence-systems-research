import base64
import datetime
import hashlib
import hmac
import json
import os
import threading

# ponytail: External Anchor and Checkpoint Verification Engine (SPEC-001 Invariant 5 Hardening).
# Protects against full-history rewrites by creating signed checkpoint receipts
# designed for publication to external append-only transparency logs (RFC 6962 / Rekor / RFC 3161).

class CheckpointAnchor:
    def __init__(self, signing_key_bytes=None, anchor_store_dir=None):
        if anchor_store_dir is None:
            anchor_store_dir = os.path.join(os.getcwd(), ".intelligence", "anchors")
        self.anchor_store_dir = os.path.abspath(anchor_store_dir)
        os.makedirs(self.anchor_store_dir, exist_ok=True)
        # Default symmetric HMAC key for lightweight local signing (can be replaced by Ed25519/x509)
        self.signing_key = signing_key_bytes or b"jonas-abde-immutable-attestation-root-2026"
        self._lock = threading.RLock()

    def create_checkpoint(self, mission_id, epoch_index, event_hash):
        """
        Creates a cryptographically signed checkpoint receipt for the current trajectory event_hash.
        """
        payload = {
            "mission_id": mission_id,
            "epoch": epoch_index,
            "event_hash": event_hash,
            "anchored_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "signer": "urn:authority:checkpoint-witness:v1"
        }
        canonical_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        signature = hmac.new(self.signing_key, canonical_bytes, hashlib.sha256).hexdigest()

        anchor_record = dict(payload)
        anchor_record["signature"] = signature

        # Save to persistent anchor store
        safe_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in mission_id)
        anchor_file = os.path.join(self.anchor_store_dir, f"{safe_id}_anchors.jsonl")

        with self._lock:
            with open(anchor_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(anchor_record, sort_keys=True) + "\n")

        return anchor_record

    def verify_anchored_trajectory(self, trajectory_events, anchor_records):
        """
        Verifies that:
        1. All anchor signatures are mathematically valid under the trusted signing key.
        2. The trajectory's event_hash at epoch k matches the signed external checkpoint.
        3. Catches full-history rewrites even if internal hash-chain was recomputed.
        """
        if not anchor_records:
            return False, "No external anchors provided for verification"

        # 1. Verify signatures on anchors
        for idx, anchor in enumerate(anchor_records):
            sig = anchor.get("signature")
            payload = {k: v for k, v in anchor.items() if k != "signature"}
            canonical_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
            expected_sig = hmac.new(self.signing_key, canonical_bytes, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                return False, f"Invalid cryptographic signature on anchor {idx} (epoch {anchor.get('epoch')})"

        # 2. Match trajectory events to anchor epochs
        for anchor in anchor_records:
            epoch = anchor["epoch"]
            expected_hash = anchor["event_hash"]

            if epoch > len(trajectory_events) or epoch <= 0:
                return False, f"Anchor epoch {epoch} outside trajectory bounds (length {len(trajectory_events)})"

            actual_event = trajectory_events[epoch - 1]
            actual_hash = actual_event.get("event_hash")

            if actual_hash != expected_hash:
                return False, (
                    f"Full-History Rewrite Detected at epoch {epoch}! "
                    f"External anchor expects {expected_hash}, but local trajectory has {actual_hash}"
                )

        return True, "Trajectory verified against external signed checkpoints"
