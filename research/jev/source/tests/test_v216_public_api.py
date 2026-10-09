import jev_engineering as jev


def test_version_is_at_least_v216():
    assert tuple(map(int, jev.__version__.split('.'))) >= (2, 16, 0)