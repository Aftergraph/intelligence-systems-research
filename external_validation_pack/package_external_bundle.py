import os
import sys
import zipfile

# ponytail: Bundles clean external validation pack for third-party teams.
# Strictly excludes internal implementation source code and notes.

def package_bundle():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    workspace = os.path.abspath(os.path.join(base_dir, ".."))
    dist_dir = os.path.join(workspace, "dist")
    os.makedirs(dist_dir, exist_ok=True)
    zip_path = os.path.join(dist_dir, "SPEC-001-EXTERNAL-VALIDATION-BUNDLE.zip")

    files_to_include = [
        ("SPECIFICATION.md", "SPECIFICATION.md"),
        ("BLINDED_INTEROPERABILITY_CHALLENGE.md", "BLINDED_INTEROPERABILITY_CHALLENGE.md"),
        ("IMPLEMENTATION_RULES_AND_RUBRIC.md", "IMPLEMENTATION_RULES_AND_RUBRIC.md"),
        ("conformance/test_cases.json", "conformance/test_cases.json"),
        ("conformance/standalone_runner.py", "conformance/standalone_runner.py")
    ]

    # Include all schemas and test vectors
    for folder in ["schemas", "test_vectors"]:
        folder_path = os.path.join(base_dir, folder)
        for root, _, files in os.walk(folder_path):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, base_dir)
                files_to_include.append((rel_path, rel_path))

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_src, arcname in files_to_include:
            src_full = os.path.join(base_dir, rel_src)
            if os.path.exists(src_full):
                zf.write(src_full, arcname)

    print(f"Created clean external validation pack: {zip_path}")
    print(f"Total files bundled: {len(files_to_include)} (strictly zero internal implementations)")
    return zip_path

if __name__ == "__main__":
    package_bundle()
