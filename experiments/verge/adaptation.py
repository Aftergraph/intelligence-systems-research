from __future__ import annotations


class ProbabilityMatcher:
    def __init__(self, operators: tuple[str, ...], minimum: float = 0.05) -> None:
        if not operators:
            raise ValueError("operators must not be empty")
        if minimum < 0 or minimum * len(operators) >= 1:
            raise ValueError("minimum is incompatible with operator count")
        self._minimum = minimum
        self._credits = {name: 1.0 for name in operators}

    def probabilities(self) -> dict[str, float]:
        count = len(self._credits)
        residual = 1.0 - self._minimum * count
        total = sum(max(0.0, value) for value in self._credits.values())
        if total == 0:
            share = 1.0 / count
            return {name: share for name in self._credits}
        return {
            name: self._minimum + residual * max(0.0, credit) / total
            for name, credit in self._credits.items()
        }


    def update(self, operator: str, improvement: float, feasible: bool) -> None:
        if operator not in self._credits:
            raise KeyError(operator)
        if not feasible or improvement <= 0:
            return
        self._credits[operator] += float(improvement)

    def credit(self, operator: str) -> float:
        return self._credits[operator]
