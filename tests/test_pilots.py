import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from pilots.run_all_pilots import run_gitops_pilot, run_data_pipeline_pilot, run_sre_incident_pilot

def test_enterprise_pilots_suite():
    res1 = run_gitops_pilot()
    assert res1["status"] == "VERIFIED"
    assert res1["events"] >= 5

    res2 = run_data_pipeline_pilot()
    assert res2["status"] == "BUDGET_CONTAINED"

    res3 = run_sre_incident_pilot()
    assert res3["status"] == "VERIFIED"

    print("SUCCESS: Phase H Enterprise Pilots validated.")

if __name__ == "__main__":
    test_enterprise_pilots_suite()
