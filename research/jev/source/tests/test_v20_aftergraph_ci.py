from pathlib import Path


def test_v20_aftergraph_workflow_is_manual_self_hosted_and_secret_free():
    root = Path(__file__).resolve().parents[1]
    text = (root / ".github/workflows/v20-mtls-fabric-aftergraph.yml").read_text()
    assert "workflow_dispatch:" in text
    assert "push:" not in text and "pull_request:" not in text
    assert "runs-on: [self-hosted, linux, x64, aftergraph-ci]" in text
    assert "jev-one v2-demo" in text
    assert "${{ secrets." not in text
