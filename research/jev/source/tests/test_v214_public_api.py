import json
from typer.testing import CliRunner
import jev_engineering as jev
from jev_engineering.cli import app


def test_version_is_v214():
    assert tuple(map(int, jev.__version__.split("."))) >= (2, 14, 0)


def test_adaptive_symbols_exported():
    for name in ["AdaptiveCompetenceRouter","AdaptiveTopologyRewriter","CompetenceLedger","CrossProviderReceiptChain","VerifiedOutcome"]:
        assert hasattr(jev,name)


def test_v214_demo_is_claim_safe():
    result=CliRunner().invoke(app,["v214-demo"])
    assert result.exit_code==0, result.output
    data=json.loads(result.stdout)
    assert data["mode"]=="v2.14-adaptive-heterogeneous-swarm"
    assert data["verified_outcome_learning"] is True
    assert data["receipt_chain_verified"] is True
    assert data["provider_calls"]==0
    assert data["live_provider_measurement"] is False