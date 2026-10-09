from collections_utils import stable_unique

def test_preserves_order(): assert stable_unique([3, 1, 3, 2, 1]) == [3, 1, 2]
def test_handles_unhashable_values():
    a = {"x": 1}; b = {"x": 2}
    assert stable_unique([a, b, a]) == [a, b]
