from pathlib import Path


def test_v18_aftergraph_runner_workflow_is_manual_and_self_hosted() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / ".github/workflows/v18-networked-kernel-aftergraph.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "push:" not in text
    assert "pull_request:" not in text
    assert "runs-on: [self-hosted, linux, x64, aftergraph-ci]" in text
    assert "jev-one networked-demo" in text
    assert "verify_no_secrets.py" in text
