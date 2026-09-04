import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from security.fuzzer import run_adversarial_fuzzing

def test_adversarial_fuzzer_resilience():
    # Run a quick 50-iteration fuzzing pass
    report = run_adversarial_fuzzing(num_iterations=50, seed=999)
    assert report["status"] == "RESILIENT"
    assert report["rejected"] > 80
    print(f"SUCCESS: Fuzzer resilience passed with {report['rejected']} vectors rejected.")

if __name__ == "__main__":
    test_adversarial_fuzzer_resilience()
