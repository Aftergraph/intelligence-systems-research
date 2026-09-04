import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from experiments.live_benchmark.dry_run_test import test_live_harness_dry_run

def test_benchmark_harness_integration():
    test_live_harness_dry_run()

if __name__ == "__main__":
    test_benchmark_harness_integration()
