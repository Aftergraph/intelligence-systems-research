#!/usr/bin/env python3
"""STUDY-006 recruitment packager — bundles participant-ready materials.

Produces: dist/STUDY-006-RECRUITMENT-PACK.zip containing:
  - RECRUITMENT-POST.md (the participant call-to-action)
  - CONSENT-FORM.md (IRB/ethics-ready consent)
  - SESSION-SCRIPT.md (moderator guide)
  - PARTICIPANT-RECRUITMENT-PLAN.md (outreach strategy)
  - instruments/ (NASA-TLX, SUS, trust calibration, session logging)

Usage:
  python package_study006_recruitment.py

Exit codes: 0 = packaged, 1 = missing files.
"""
import os
import sys
import zipfile
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
PILOTS = WORKSPACE / "pilots"
DIST = WORKSPACE / "dist"
ZIP_NAME = "STUDY-006-RECRUITMENT-PACK.zip"

FILES = [
    "RECRUITMENT-POST.md",
    "CONSENT-FORM.md",
    "SESSION-SCRIPT.md",
    "PARTICIPANT-RECRUITMENT-PLAN.md",
]


def main() -> int:
    DIST.mkdir(exist_ok=True)
    zip_path = DIST / ZIP_NAME
    missing = []

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in FILES:
            fpath = PILOTS / fname
            if fpath.is_file():
                zf.write(fpath, fname)
            else:
                missing.append(fname)

        # Instruments directory
        instruments = PILOTS / "instruments"
        if instruments.is_dir():
            for f in sorted(instruments.glob("*")):
                if f.is_file():
                    zf.write(f, f"instruments/{f.name}")
        else:
            missing.append("instruments/")

    if missing:
        print(json.dumps({"ok": False, "missing": missing}))
        return 1

    print(f"Created recruitment pack: {zip_path}")
    print(f"Files: {len(FILES) + len(list((PILOTS / 'instruments').glob('*')))}")
    return 0


if __name__ == "__main__":
    import json
    sys.exit(main())
