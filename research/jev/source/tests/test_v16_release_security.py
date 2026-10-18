from pathlib import Path
import subprocess
import sys


def test_release_secret_scan_passes() -> None:
    root = Path(__file__).resolve().parents[1]
    r = subprocess.run([sys.executable, str(root / 'scripts' / 'verify_no_secrets.py'), str(root)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert 'SECRET_SCAN=PASS' in r.stdout


def test_live_provider_workflow_uses_github_secrets_and_manual_trigger() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / '.github/workflows/live-provider-smoke.yml').read_text(encoding='utf-8')
    assert 'workflow_dispatch:' in text
    assert 'pull_request:' not in text
    assert 'push:' not in text
    assert 'environment: provider-smoke' in text
    assert '${{ secrets.TYPESAFE_API_KEY }}' in text
    assert '${{ secrets.DIALAGRAM_API_KEY }}' in text
    assert 'jev-one live-smoke' in text
