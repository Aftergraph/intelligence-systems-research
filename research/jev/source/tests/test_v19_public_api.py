import jev_engineering as j


def test_v19_public_api_exports():
    for name in [
        "NodeProtocol", "NodeRequest", "NodeResponse", "SignedNodeMessage",
        "HttpNodeTransport", "InMemoryNodeEndpoint", "RemoteWorkerClient",
        "RemoteExecutionResult", "ProofDelta", "ProofReplicator",
    ]:
        assert hasattr(j, name), name
    assert tuple(map(int, j.__version__.split("."))) >= (2, 8, 0)
