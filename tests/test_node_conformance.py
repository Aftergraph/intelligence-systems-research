import os
import shutil
import subprocess
import pytest

# ponytail: Automated Node.js clean-room conformance check.
# Ensures that SPEC-001 cross-platform Node.js implementation maintains 100% pass rate.

def test_node_clean_room_conformance():
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js runtime not installed on host environment")

    workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    runner_path = os.path.join(
        workspace, "external_validation_pack", "implementations", "node_runtime", "conformance_runner.js"
    )

    result = subprocess.run([node_bin, runner_path], capture_output=True, text=True, cwd=workspace)
    assert result.returncode == 0, f"Node.js runner failed: {result.stderr}\n{result.stdout}"
    assert "14/14 Passed (100.0%)" in result.stdout
    print("SUCCESS: Clean-room Node.js engine passed all 14 conformance tests.")

if __name__ == "__main__":
    test_node_clean_room_conformance()
