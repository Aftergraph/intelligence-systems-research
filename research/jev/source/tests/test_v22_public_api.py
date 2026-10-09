import jev_engineering as j

def test_v22_public_api():
    assert tuple(map(int, j.__version__.split("."))) >= (2, 8, 0)
    assert j.NodeAgent
    assert j.NodeAgentConfig
