from __future__ import annotations

from pathlib import Path


def test_v26_aftergraph_workflow_is_manual_self_hosted_and_secret_free():
    text = Path('.github/workflows/v26-system-efficiency-aftergraph.yml').read_text(encoding='utf-8')
    assert 'workflow_dispatch:' in text
    assert 'push:' not in text
    assert 'pull_request:' not in text
    assert 'runs-on: [self-hosted, linux, x64, aftergraph-ci]' in text
    assert 'v26-demo' in text
    assert 'verify_no_secrets.py' in text
    assert 'TYPESAFE_API_KEY' not in text
    assert 'DIALAGRAM_API_KEY' not in text
