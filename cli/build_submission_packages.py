import hashlib
import json
import os
import zipfile

# ponytail: Automated Submission Package Builder (USPTO, IEEE-SA, NIST).
# Assembles filing-ready archives and generates cryptographic SHA-256 manifests.

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def build_packages():
    workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dist_dir = os.path.join(workspace, "dist")
    os.makedirs(dist_dir, exist_ok=True)

    manifest = {
        "generator": "Jonas Abde Research Program Package Builder v1.0",
        "date": "2026-09-04",
        "packages": {}
    }

    # =========================================================================
    # 1. USPTO Provisional Patent Application Package
    # =========================================================================
    patent_src = os.path.join(workspace, "ip", "provisional_patent_application")
    patent_zip_path = os.path.join(dist_dir, "uspto_provisional_patent_package.zip")
    patent_files = [
        os.path.join(patent_src, "SPECIFICATION.md"),
        os.path.join(patent_src, "FORM_PTO_SB_16_COVER_SHEET.md"),
        os.path.join(workspace, "ip", "PATENT-PRIOR-ART-AND-CLAIMS-ANALYSIS.md"),
        os.path.join(workspace, "ip", "PRIVATE-INVENTION-RECORD-001.md")
    ]

    with zipfile.ZipFile(patent_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        file_hashes = {}
        for fpath in patent_files:
            if os.path.exists(fpath):
                arcname = os.path.basename(fpath)
                zipf.write(fpath, arcname=arcname)
                file_hashes[arcname] = compute_sha256(fpath)

    manifest["packages"]["uspto_patent"] = {
        "archive": "uspto_provisional_patent_package.zip",
        "sha256": compute_sha256(patent_zip_path),
        "files": file_hashes
    }
    print(f"[OK] Built USPTO Provisional Patent Package: {patent_zip_path}")

    # =========================================================================
    # 2. IEEE-SA Standards Submission Package
    # =========================================================================
    ieee_src = os.path.join(workspace, "standards", "ieee_submission_package")
    ieee_zip_path = os.path.join(dist_dir, "ieee_standards_submission_package.zip")
    ieee_files = [
        os.path.join(ieee_src, "FORM_PAR_PROJECT_AUTHORIZATION_REQUEST.md"),
        os.path.join(ieee_src, "IEEE_LOI_RAND_Z_PATENT_STATEMENT.md"),
        os.path.join(workspace, "standards", "RFC-0001-INTELLIGENCE-SYSTEM-CONTRACT.md"),
        os.path.join(workspace, "standards", "STANDARDS-CROSSWALK.md"),
        os.path.join(workspace, "standards", "GOVERNANCE-AND-WORKING-GROUP-CHARTER.md"),
        os.path.join(workspace, "SPEC-001-MISSION-CONTRACT-v0.1.md")
    ]

    # Include normative schemas
    schemas_dir = os.path.join(workspace, "schemas")
    schema_files = [os.path.join(schemas_dir, s) for s in os.listdir(schemas_dir) if s.endswith(".json")]

    with zipfile.ZipFile(ieee_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        ieee_hashes = {}
        for fpath in ieee_files:
            if os.path.exists(fpath):
                arcname = os.path.basename(fpath)
                zipf.write(fpath, arcname=arcname)
                ieee_hashes[arcname] = compute_sha256(fpath)
        for sf in schema_files:
            arcname = os.path.join("schemas", os.path.basename(sf))
            zipf.write(sf, arcname=arcname)
            ieee_hashes[arcname] = compute_sha256(sf)

    manifest["packages"]["ieee_standards"] = {
        "archive": "ieee_standards_submission_package.zip",
        "sha256": compute_sha256(ieee_zip_path),
        "files": ieee_hashes
    }
    print(f"[OK] Built IEEE-SA Submission Package: {ieee_zip_path}")

    # =========================================================================
    # 3. NIST TEVV-Athlon Submission Package
    # =========================================================================
    nist_src = os.path.join(workspace, "standards", "nist_submission_package")
    nist_zip_path = os.path.join(dist_dir, "nist_tevv_submission_package.zip")
    nist_files = [
        os.path.join(nist_src, "NIST_TEVV_ATHLON_SUBMISSION_DOSSIER.md"),
        os.path.join(workspace, "STUDY-002-JAR-EXP-0001-EMPIRICAL-EVALUATION.md"),
        os.path.join(workspace, "STUDY-003-MISSION-BENCH-ABLATION-REPORT.md"),
        os.path.join(workspace, "STUDY-005-CONFOUNDER-ANALYSIS-REPORT.md")
    ]

    with zipfile.ZipFile(nist_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        nist_hashes = {}
        for fpath in nist_files:
            if os.path.exists(fpath):
                arcname = os.path.basename(fpath)
                zipf.write(fpath, arcname=arcname)
                nist_hashes[arcname] = compute_sha256(fpath)

    manifest["packages"]["nist_tevv"] = {
        "archive": "nist_tevv_submission_package.zip",
        "sha256": compute_sha256(nist_zip_path),
        "files": nist_hashes
    }
    # =========================================================================
    # 4. External Blind Validation Package vNext (SDO & Third-Party Challenge)
    # =========================================================================
    vnext_src = os.path.join(workspace, "external_validation_pack_vNext")
    vnext_zip_path = os.path.join(dist_dir, "SPEC-001-EXTERNAL-VALIDATION-vNext-BUNDLE.zip")
    with zipfile.ZipFile(vnext_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        vnext_hashes = {}
        for root, _, files in os.walk(vnext_src):
            for file in files:
                if "__pycache__" in root or file.endswith(".pyc"):
                    continue
                fpath = os.path.join(root, file)
                rel_path = os.path.relpath(fpath, vnext_src)
                zipf.write(fpath, arcname=rel_path)
                vnext_hashes[rel_path] = compute_sha256(fpath)

    manifest["packages"]["external_validation_vnext"] = {
        "archive": "SPEC-001-EXTERNAL-VALIDATION-vNext-BUNDLE.zip",
        "sha256": compute_sha256(vnext_zip_path),
        "files": vnext_hashes
    }
    print(f"[OK] Built External Validation vNext Bundle: {vnext_zip_path}")

    # Write overall manifest
    manifest_path = os.path.join(dist_dir, "SUBMISSION_MANIFEST.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"[OK] Cryptographic Submission Manifest generated: {manifest_path}")

    return manifest

if __name__ == "__main__":
    build_packages()
