import datetime
import subprocess
import uuid

# ponytail: minimal deterministic evidence verifier module.
# Evaluates exit codes, stdout, or custom test functions and produces
# compliant EvidenceItem objects conforming to schemas/evidence.v0alpha1.json.

class DeterministicTestVerifier:
    def __init__(self, identifier="deterministic-harness-v1", version="1.0.0"):
        self.identifier = identifier
        self.version = version

    def verify_command(self, mission_id, criterion_ref, command, cwd=None, timeout=30):
        """Runs an external command (e.g. pytest or lint) and captures deterministic proof."""
        start_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            res = subprocess.run(
                command,
                cwd=cwd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            exit_code = res.returncode
            stdout = res.stdout
            stderr = res.stderr
            status = "SATISFIED" if exit_code == 0 else "FAILED"
        except subprocess.TimeoutExpired as e:
            exit_code = -1
            stdout = str(e.stdout or "")
            stderr = f"Timeout expired after {timeout}s"
            status = "FAILED"
        except Exception as e:
            exit_code = -2
            stdout = ""
            stderr = f"Execution error: {str(e)}"
            status = "FAILED"

        evidence_item = {
            "id": f"ev-{uuid.uuid4().hex[:8]}",
            "mission_id": mission_id,
            "criterion_ref": criterion_ref,
            "tier": "tier_2_deterministic",
            "verifier": {
                "type": "test_harness",
                "identifier": self.identifier,
                "version": self.version
            },
            "result": status,
            "evidence_data": {
                "exit_code": exit_code,
                "stdout": stdout[:2000],  # budget limit
                "stderr": stderr[:2000]
            },
            "timestamp": start_time,
            "freshness_seconds": 3600
        }
        return evidence_item

    def verify_callable(self, mission_id, criterion_ref, test_fn):
        """Runs a python callable returning (bool_success, output_str)."""
        start_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            success, output = test_fn()
            status = "SATISFIED" if success else "FAILED"
            exit_code = 0 if success else 1
            stderr = ""
        except Exception as e:
            status = "FAILED"
            exit_code = -1
            output = ""
            stderr = str(e)

        return {
            "id": f"ev-{uuid.uuid4().hex[:8]}",
            "mission_id": mission_id,
            "criterion_ref": criterion_ref,
            "tier": "tier_2_deterministic",
            "verifier": {
                "type": "test_harness",
                "identifier": self.identifier,
                "version": self.version
            },
            "result": status,
            "evidence_data": {
                "exit_code": exit_code,
                "stdout": str(output)[:2000],
                "stderr": stderr[:2000]
            },
            "timestamp": start_time,
            "freshness_seconds": 3600
        }
