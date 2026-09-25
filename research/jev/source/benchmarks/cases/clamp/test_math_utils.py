from math_utils import clamp

def test_clamp_below(): assert clamp(-2, 0, 10) == 0
def test_clamp_inside(): assert clamp(4, 0, 10) == 4
def test_clamp_above(): assert clamp(20, 0, 10) == 10
