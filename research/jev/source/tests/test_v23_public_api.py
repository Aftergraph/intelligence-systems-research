import jev_engineering as j


def test_v23_public_api():
    assert tuple(map(int, j.__version__.split("."))) >= (2, 8, 0)
    assert j.RelayHubServer
    assert j.RelayNodeAgent
    assert j.RelayCoordinatorClient
    assert j.RelayNodeService
    assert j.RelayNodeClientSession
    assert j.RelayHubConfig
    assert j.RelayNodeConfig
    assert j.RelayClientConfig
    assert j.build_node_gateway
