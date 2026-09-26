from pathlib import Path
import jev_engineering as jev
from typer.testing import CliRunner
from jev_engineering.cli import app

def test_v213_exports():
    for name in (
        'BackendKind','BackendIdentity','BackendBinding','BackendExecution','BackendRegistry',
        'CompetenceRouter','RouteDecision','TopologyMode','TopologyDecision','DynamicTopologySelector',
        'SignedSubagentReceipt','HeterogeneousSubagentExecutor',
    ):
        assert hasattr(jev, name), name

def test_v213_version():
    assert jev.__version__ == '2.13.0'

def test_v213_schemas_exist():
    root=Path(jev.__file__).parent/'schemas'
    assert (root/'backend-registry.v1.schema.json').is_file()
    assert (root/'subagent-execution-receipt.v1.schema.json').is_file()

def test_v213_demo_is_claim_safe():
    r=CliRunner().invoke(app,['v213-demo'])
    assert r.exit_code==0, r.output
    assert '"accepted": true' in r.output
    assert '"backend_count": 2' in r.output
    assert '"receipts_verify": true' in r.output
    assert '"authenticated_live_provider_execution": false' in r.output
    assert '"provider_calls": 0' in r.output