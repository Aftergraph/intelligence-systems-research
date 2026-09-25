from __future__ import annotations

import jev_engineering as j


def test_v26_public_api_and_version():
    assert tuple(map(int, j.__version__.split("."))) >= (2, 8, 0)
    for name in (
        "FrontierWorkloadProfile",
        "EfficiencyLever",
        "SystemEfficiencyPlan",
        "AttainableRegion",
        "SystemEfficiencyCompiler",
        "AdaptiveContextBudgeter",
        "EarlyExitGate",
        "RetryBudgetOptimizer",
    ):
        assert hasattr(j, name), name
