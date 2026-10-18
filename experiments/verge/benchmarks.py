from __future__ import annotations

import math
from collections.abc import Sequence


def sphere(x: Sequence[float]) -> float:
    return sum(value * value for value in x)


def rosenbrock(x: Sequence[float]) -> float:
    return sum(
        100.0 * (x[i + 1] - x[i] * x[i]) ** 2 + (1.0 - x[i]) ** 2
        for i in range(len(x) - 1)
    )


def rastrigin(x: Sequence[float]) -> float:
    return 10.0 * len(x) + sum(
        value * value - 10.0 * math.cos(2.0 * math.pi * value)
        for value in x
    )


def ackley(x: Sequence[float]) -> float:
    if not x:
        return 0.0
    n = len(x)
    square_mean = sum(value * value for value in x) / n
    cosine_mean = sum(math.cos(2.0 * math.pi * value) for value in x) / n
    return -20.0 * math.exp(-0.2 * math.sqrt(square_mean)) - math.exp(cosine_mean) + math.e + 20.0
