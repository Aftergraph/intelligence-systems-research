#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
errors: list[str] = []

# Version truth must agree across user-visible/package surfaces.
pyproject = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
init_py = (ROOT / 'src/jev_engineering/__init__.py').read_text(encoding='utf-8')
readme = (ROOT / 'README.md').read_text(encoding='utf-8')
pm = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
im = re.search(r'^__version__\s*=\s*"([^"]+)"', init_py, re.M)
rm = re.search(r'^# Aftergraph Jev Engineering v([^\s]+)', readme, re.M)
versions = {'pyproject': pm.group(1) if pm else None, 'package': im.group(1) if im else None, 'readme': rm.group(1) if rm else None}
if len(set(versions.values())) != 1 or None in versions.values():
    errors.append(f'version drift: {versions}')

# Shipped evidence must not contain build-container absolute paths.
preflight_path = ROOT / 'BENCHMARK_PREFLIGHT.json'
if preflight_path.exists():
    raw = preflight_path.read_text(encoding='utf-8')
    for marker in ('/mnt/data/', '/tmp/', '\\\\mnt\\data\\'):
        if marker in raw:
            errors.append(f'BENCHMARK_PREFLIGHT.json contains stale absolute path marker: {marker}')
    try:
        json.loads(raw)
    except json.JSONDecodeError as exc:
        errors.append(f'BENCHMARK_PREFLIGHT.json invalid JSON: {exc}')

# GitHub Actions dependencies must be immutable SHA pins, not mutable tags.
uses_re = re.compile(r'^\s*-?\s*uses:\s*([^\s#]+)', re.M)
sha_re = re.compile(r'^[^@]+@[0-9a-f]{40}$')
for workflow in sorted((ROOT / '.github/workflows').glob('*.yml')):
    text = workflow.read_text(encoding='utf-8')
    for ref in uses_re.findall(text):
        if ref.startswith('./') or ref.startswith('docker://'):
            continue
        if not sha_re.match(ref):
            errors.append(f'{workflow.relative_to(ROOT)} mutable action ref: {ref}')

if errors:
    print('RELEASE_RELOCATABLE=FAIL')
    for error in errors:
        print(error)
    raise SystemExit(2)
print(f'RELEASE_RELOCATABLE=PASS version={versions["pyproject"]}')
