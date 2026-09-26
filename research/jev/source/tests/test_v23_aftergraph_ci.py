from pathlib import Path


def test_v23_aftergraph_workflow_is_manual_self_hosted_and_secret_free():
    path = Path('.github/workflows/v23-outbound-relay-aftergraph.yml')
    text = path.read_text(encoding='utf-8')
    assert 'workflow_dispatch:' in text
    assert 'push:' not in text
    assert 'pull_request:' not in text
    assert 'runs-on: [self-hosted, linux, x64, aftergraph-ci]' in text
    assert 'jev-one v23-demo' in text
    assert '${{ secrets.' not in text
