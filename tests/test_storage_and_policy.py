import json
import os
import shutil
import sys
import tempfile
import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from runtime.storage import TrajectoryStorage
from runtime.policy import PolicyEngine

def test_trajectory_hash_chain_and_tamper_detection():
    temp_dir = tempfile.mkdtemp()
    try:
        storage = TrajectoryStorage(base_dir=temp_dir)
        m_id = "test-mission-audit"

        # Append 5 events
        for i in range(1, 6):
            storage.append_event(m_id, {
                "event_id": f"evt-{i}",
                "event_type": "ACTION_EXECUTED",
                "step": i,
                "data": f"Step {i} executed successfully"
            })

        log_path = storage.get_trajectory_path(m_id)
        assert os.path.exists(log_path)

        # 1. Verify integrity of pristine log
        valid, msg = TrajectoryStorage.verify_chain_integrity(log_path)
        assert valid is True
        assert "tamper-free" in msg

        # 2. Tamper with line 3 content
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        tampered_record = json.loads(lines[2])
        tampered_record["data"] = "Adversary altered this step data!"
        lines[2] = json.dumps(tampered_record) + "\n"

        with open(log_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        # 3. Verify that tampering is detected
        valid_tampered, err_msg = TrajectoryStorage.verify_chain_integrity(log_path)
        assert valid_tampered is False
        assert "Tampered event content at line 3" in err_msg
        print("SUCCESS: Cryptographic hash chain detected event tampering at line 3.")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_policy_engine_filesystem_and_command_boundaries():
    temp_dir = tempfile.mkdtemp()
    try:
        allowed_sub = os.path.join(temp_dir, "workspace")
        os.makedirs(allowed_sub, exist_ok=True)

        policy = PolicyEngine({
            "allow_paths": [allowed_sub],
            "deny_paths": [os.path.join(allowed_sub, "secret")],
            "denied_commands": ["rm -rf /", "drop database"]
        })

        # Allowed path
        safe_file = os.path.join(allowed_sub, "app.py")
        assert policy.validate_file_access(safe_file) is True

        # Explicit deny path
        secret_file = os.path.join(allowed_sub, "secret", "keys.txt")
        with pytest.raises(PermissionError) as exc:
            policy.validate_file_access(secret_file)
        assert "explicitly denied" in str(exc.value)

        # Path outside workspace
        outside_file = os.path.join(temp_dir, "other.txt")
        with pytest.raises(PermissionError) as exc:
            policy.validate_file_access(outside_file)
        assert "outside allowed workspace" in str(exc.value)

        # Sensitive file (.env)
        env_file = os.path.join(allowed_sub, ".env")
        with pytest.raises(PermissionError) as exc:
            policy.validate_file_access(env_file)
        assert "sensitive file" in str(exc.value)

        # Command blacklist
        assert policy.validate_command("npm test") is True
        with pytest.raises(PermissionError) as exc:
            policy.validate_command("rm -rf / --no-preserve-root")
        assert "Destructive command blocked" in str(exc.value)

        print("SUCCESS: PolicyEngine sandbox and command containment verified.")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    test_trajectory_hash_chain_and_tamper_detection()
    test_policy_engine_filesystem_and_command_boundaries()
