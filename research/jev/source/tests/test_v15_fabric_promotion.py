from pathlib import Path

from jev_engineering.intelligence_fabric import (
    DecisionRequest,
    FrontierTokenBudget,
    IntelligenceBid,
    IntelligenceFabric,
)
from jev_engineering.shadow_runtime import PromotionRegistry
from jev_engineering.learning import LearningCandidate, LearningState


def test_promoted_route_is_preferred_but_still_cannot_bypass_quality_or_authority(tmp_path: Path):
    registry = PromotionRegistry(path=tmp_path / "routes.json")
    registry.register(LearningCandidate(
        candidate_id="evidence-backed",
        decision_family="safe_to_run",
        incumbent_strategy="rule",
        candidate_strategy="jev",
        state=LearningState.PROMOTED,
        holdout_runs=1,
        holdout_successes=1,
    ))
    bids = [
        IntelligenceBid("rule", "rule", ("decision",), 0.99, 0.001, 1.0),
        IntelligenceBid("jev", "jev", ("decision",), 0.95, 0.002, 2.0),
    ]
    fabric = IntelligenceFabric(
        bids=bids,
        frontier_budget=FrontierTokenBudget(0, 0),
        promotion_registry=registry,
    )
    request = DecisionRequest(
        request_id="r1",
        capability="decision",
        required_vsr=0.90,
        state_features={"decision_family": "safe_to_run"},
    )
    assert fabric.select_request(request).strategy_id == "jev"

    # Promoted routes remain subject to the same admissibility gates.
    too_strict = DecisionRequest(
        request_id="r2",
        capability="decision",
        required_vsr=0.98,
        state_features={"decision_family": "safe_to_run"},
    )
    assert fabric.select_request(too_strict).strategy_id == "rule"
