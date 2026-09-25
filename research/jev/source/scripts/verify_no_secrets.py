#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "build", ".jev", ".jev-one"}
SKIP_FILES = {".env.example"}
PATTERNS = {
    "typesafe_api_key": re.compile(rb"apikey_[A-Za-z0-9_-]{24,}"),
    "dialagram_api_key": re.compile(rb"dgr_live_[A-Za-z0-9_-]{24,}"),
}

hits: list[str] = []
for path in ROOT.rglob("*"):
    if not path.is_file():
        continue
    rel = path.relative_to(ROOT)
    if any(part in SKIP_DIRS for part in rel.parts) or path.name in SKIP_FILES:
        continue
    try:
        data = path.read_bytes()
    except OSError:
        continue
    if len(data) > 5_000_000:
        continue
    for name, pattern in PATTERNS.items():
        if pattern.search(data):
            hits.append(f"{rel.as_posix()}: {name}")
if hits:
    print("SECRET_SCAN=FAIL")
    for hit in hits:
        print(hit)
    raise SystemExit(2)
print("SECRET_SCAN=PASS")
