from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True, slots=True)
class WilsonInterval:
    successes: int
    trials: int
    lower: float
    upper: float


def wilson_interval(successes: int, trials: int, *, z: float = 1.959963984540054) -> WilsonInterval:
    if trials <= 0:
        raise ValueError("trials must be positive")
    if successes < 0 or successes > trials:
        raise ValueError("successes must be between 0 and trials")
    p = successes / trials
    z2 = z * z
    denom = 1 + z2 / trials
    centre = p + z2 / (2 * trials)
    spread = z * sqrt((p * (1 - p) + z2 / (4 * trials)) / trials)
    return WilsonInterval(successes, trials, max(0.0, (centre - spread) / denom), min(1.0, (centre + spread) / denom))
