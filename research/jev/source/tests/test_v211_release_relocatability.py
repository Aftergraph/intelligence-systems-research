from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from jev_engineering.benchmark import preflight_manifest


def test_preflight_report_preserves_relative_paths(tmp_path: Path, monkeypatch):
    configs = tmp_path / 'configs'
    benchmarks = tmp_path / 'benchmarks'
    case = benchmarks / 'cases' / 'x'
    configs.mkdir()
    case.mkdir(parents=True)
    (configs / 'a.yaml').write_text('''
decision:
  backend: typesafe
  api_key_env: TYPESAFE_TEST
models:
  qwen:
    provider: dialagram
    model: qwen-3.8-max-thinking
    tier: frontier
    transport: openai_compatible
    base_url: https://dialagram.me/router/v1
    api_key_env: DIALAGRAM_TEST
''', encoding='utf-8')
    manifest = benchmarks / 'bench.yaml'
    manifest.write_text('''
version: 1
conditions:
  - id: jev
    config: ../configs/a.yaml
cases:
  - id: x
    source: cases/x
    task: fix x
    verify: python -m pytest -q
''', encoding='utf-8')
    monkeypatch.delenv('TYPESAFE_TEST', raising=False)
    monkeypatch.delenv('DIALAGRAM_TEST', raising=False)
    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        report = preflight_manifest(Path('benchmarks/bench.yaml'))
    finally:
        os.chdir(cwd)
    assert report['manifest'] == 'benchmarks/bench.yaml'
    assert report['conditions'][0]['config'] == '../configs/a.yaml'
    assert report['cases'][0]['source'] == 'cases/x'
    assert '/mnt/data/' not in json.dumps(report)


def test_release_relocatability_gate_passes_repository():
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, str(root / 'scripts/verify_release_relocatable.py'), str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert 'RELEASE_RELOCATABLE=PASS' in proc.stdout
