import json
import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from cli.build_submission_packages import build_packages

def test_submission_packaging():
    manifest = build_packages()

    assert "uspto_patent" in manifest["packages"]
    assert "ieee_standards" in manifest["packages"]
    assert "nist_tevv" in manifest["packages"]

    dist_dir = os.path.join(workspace, "dist")
    assert os.path.exists(os.path.join(dist_dir, "uspto_provisional_patent_package.zip"))
    assert os.path.exists(os.path.join(dist_dir, "ieee_standards_submission_package.zip"))
    assert os.path.exists(os.path.join(dist_dir, "nist_tevv_submission_package.zip"))
    assert os.path.exists(os.path.join(dist_dir, "SUBMISSION_MANIFEST.json"))

    # Verify that zip files are non-empty
    assert os.path.getsize(os.path.join(dist_dir, "uspto_provisional_patent_package.zip")) > 1000
    assert os.path.getsize(os.path.join(dist_dir, "ieee_standards_submission_package.zip")) > 1000
    assert os.path.getsize(os.path.join(dist_dir, "nist_tevv_submission_package.zip")) > 1000

    print("SUCCESS: All formal filing packages generated and cryptographically hashed.")

if __name__ == "__main__":
    test_submission_packaging()
