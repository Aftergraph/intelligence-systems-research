from pathlib import Path


def test_v25_aftergraph_workflow_is_manual_self_hosted_and_secret_scoped():
    text = Path('.github/workflows/v25-evidence-campaign-aftergraph.yml').read_text(encoding='utf-8')
    assert 'workflow_dispatch:' in text
    assert 'push:' not in text
    assert 'pull_request:' not in text
    assert 'runs-on: [self-hosted, linux, x64, aftergraph-ci]' in text
    assert 'environment: provider-smoke' in text
    assert '${{ secrets.TYPESAFE_API_KEY }}' in text
    assert '${{ secrets.DIALAGRAM_API_KEY }}' in text
    assert 'live-campaign-v25' in text
    assert 'campaign-verify-v25' in text
