from jev_engineering import __version__


def test_v217_version():
    assert tuple(map(int, __version__.split('.'))) >= (2, 17, 0)