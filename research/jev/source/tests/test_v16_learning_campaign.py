from __future__ import annotations

import pytest

from jev_engineering.learning import LearningCandidate, PromotionPolicy
from jev_engineering.learning_campaign import CampaignState, LearningCampaign, OutcomeSample
from jev_engineering.statistics import wilson_interval


def _sample(ok: bool, cost: float, false: bool = False) -> OutcomeSample:
    return OutcomeSample(verified=ok, false_completion=false, cost_usd=cost)


def test_wilson_interval_bounds() -> None:
    ci = wilson_interval(95, 100)
    assert 0 < ci.lower < 0.95 < ci.upper <= 1


def test_campaign_promotes_cheaper_noninferior_candidate() -> None:
    candidate = LearningCandidate('c1', 'safe_to_run', 'frontier', 'jev')
    campaign = LearningCampaign(candidate, PromotionPolicy(max_fcr=0.0), min_holdout_trials=20, noninferiority_margin=0.05)
    for _ in range(20):
        campaign.record_pair(incumbent=_sample(True, 0.10), candidate=_sample(True, 0.001))
    campaign.advance(CampaignState.EXPERIMENT)
    campaign.advance(CampaignState.HOLDOUT)
    decision = campaign.promotion_decision()
    assert decision['promote'] is True
    campaign.advance(CampaignState.PROMOTED)
    assert campaign.state is CampaignState.PROMOTED


def test_campaign_quarantines_immediate_false_completion() -> None:
    candidate = LearningCandidate('c1', 'safe_to_run', 'frontier', 'jev')
    campaign = LearningCampaign(candidate, PromotionPolicy(max_fcr=0.0), min_holdout_trials=1, noninferiority_margin=1.0)
    campaign.record_pair(incumbent=_sample(True, 1.0), candidate=_sample(True, 0.1))
    campaign.advance(CampaignState.EXPERIMENT)
    campaign.advance(CampaignState.HOLDOUT)
    campaign.advance(CampaignState.PROMOTED)
    assert campaign.record_post_promotion(_sample(False, 0.1, false=True)) is False
    assert campaign.state is CampaignState.QUARANTINED


def test_campaign_refuses_small_holdout() -> None:
    campaign = LearningCampaign(LearningCandidate('c', 'd', 'a', 'b'), PromotionPolicy(), min_holdout_trials=10)
    for _ in range(3):
        campaign.record_pair(incumbent=_sample(True, 1), candidate=_sample(True, 0.1))
    assert campaign.promotion_decision()['promote'] is False
