import hashlib
import json
import os
import shutil
import sys
import tempfile

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from runtime.storage import TrajectoryStorage
from runtime.anchoring import CheckpointAnchor

def test_signed_external_anchoring_and_full_history_rewrite_detection():
    temp_dir = tempfile.mkdtemp()
    try:
        traj_dir = os.path.join(temp_dir, "trajectories")
        anchor_dir = os.path.join(temp_dir, "anchors")
        
        storage = TrajectoryStorage(base_dir=traj_dir)
        anchor_engine = CheckpointAnchor(anchor_store_dir=anchor_dir)
        mission_id = "mission-anchor-test"

        # 1. Generate legitimate execution steps
        events = []
        for i in range(1, 6):
            rec = storage.append_event(mission_id, {
                "step": i,
                "action": f"read_database_record_{i}",
                "result": "success"
            })
            events.append(rec)

        # 2. Publish an external signed checkpoint anchor at step 3 and step 5
        anchor_3 = anchor_engine.create_checkpoint(mission_id, epoch_index=3, event_hash=events[2]["event_hash"])
        anchor_5 = anchor_engine.create_checkpoint(mission_id, epoch_index=5, event_hash=events[4]["event_hash"])

        anchors = [anchor_3, anchor_5]

        # 3. Verify pristine trajectory against anchors
        loaded_events = storage.load_trajectory(mission_id)
        valid, msg = anchor_engine.verify_anchored_trajectory(loaded_events, anchors)
        assert valid is True
        assert "verified against external signed checkpoints" in msg

        # 4. Attack: Adversary performs a FULL-HISTORY REWRITE!
        # The adversary deletes step 2, creates a completely fabricated history,
        # but correctly computes all internal SHA-256 hashes so local verify_chain_integrity() passes!
        rewritten_events = []
        prev_h = "0" * 64
        for i in range(1, 6):
            payload = {
                "step": i,
                "action": f"malicious_tampered_action_{i}",
                "result": "forged_data"
            }
            c_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
            h = hashlib.sha256(prev_h.encode("utf-8") + c_bytes).hexdigest()
            record = dict(payload)
            record["prev_hash"] = prev_h
            record["event_hash"] = h
            rewritten_events.append(record)
            prev_h = h

        # 5. Show that local hash-chain verification alone passes on forged data
        fake_log = os.path.join(temp_dir, "fake.jsonl")
        with open(fake_log, "w", encoding="utf-8") as f:
            for ev in rewritten_events:
                f.write(json.dumps(ev, sort_keys=True) + "\n")

        local_valid, _ = TrajectoryStorage.verify_chain_integrity(fake_log)
        assert local_valid is True, "Local hash-chain passes on full rewrite!"

        # 6. Show that external signed anchor DETECTS the full-history rewrite!
        anchor_valid, err = anchor_engine.verify_anchored_trajectory(rewritten_events, anchors)
        assert anchor_valid is False
        assert "Full-History Rewrite Detected" in err
        print(f"SUCCESS: External signed anchoring detected full history rewrite: {err}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    test_signed_external_anchoring_and_full_history_rewrite_detection()
