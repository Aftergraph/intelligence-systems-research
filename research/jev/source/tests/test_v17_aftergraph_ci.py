from pathlib import Path


def test_aftergraph_provider_smoke_is_manual_self_hosted_and_secret_scoped() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / '.github' / 'workflows' / 'live-provider-smoke-aftergraph.yml').read_text(encoding='utf-8')
    assert 'workflow_dispatch:' in text
    assert 'push:' not in text
    assert 'pull_request:' not in text
    assert 'runs-on: [self-hosted, linux, x64, aftergraph-ci]' in text
    assert 'environment: provider-smoke' in text
    assert '${{ secrets.TYPESAFE_API_KEY }}' in text
    assert '${{ secrets.DIALAGRAM_API_KEY }}' in text
    assert 'jev-one live-smoke' in text
