from pathlib import Path

from jev_engineering.node_gateway import NodeGatewayServer


def test_gateway_uses_bounded_threading_shutdown_contract():
    # Avoid constructing TLS/gateway fixtures here; this locks the server-class contract
    # responsible for preventing completed CI tests from hanging at interpreter shutdown.
    import inspect
    source = inspect.getsource(NodeGatewayServer.__init__)
    assert "daemon_threads = True" in source
    assert "block_on_close = False" in source