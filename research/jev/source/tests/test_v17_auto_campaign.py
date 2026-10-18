from __future__ import annotations

from jev_engineering.automatic_campaign import AutoCampaignController, AutoCampaignSchedule
from jev_engineering.learning import LearningCandidate, PromotionPolicy
from jev_engineering.learning_campaign import CampaignState, LearningCampaign, OutcomeSample


def _ok(cost: float) -> OutcomeSample:
    return OutcomeSample(verified=True, false_completion=False, cost_usd=cost)


def test_auto_campaign_advances_and_promotes_after_phase_evidence() -> None:
    campaign = LearningCampaign(
        LearningCandidate('c1', 'safe_to_run', 'frontier', 'jev'),
        PromotionPolicy(max_fcr=0.0),
        min_holdout_trials=6,
        noninferiority_margin=0.1,
    )
    ctl = AutoCampaignController(campaign, AutoCampaignSchedule(shadow_pairs=2, experiment_pairs=2, holdout_pairs=2))
    for _ in range(6):
        ctl.record_pair(incumbent=_ok(0.10), candidate=_ok(0.001))
    assert campaign.state is CampaignState.PROMOTED
    assert ctl.phase_counts == {'shadow': 2, 'experiment': 2, 'holdout': 2}


def test_auto_campaign_rejects_at_holdout_gate() -> None:
    campaign = LearningCampaign(
        LearningCandidate('c1', 'safe_to_run', 'frontier', 'jev'),
        PromotionPolicy(max_fcr=0.0),
        min_holdout_trials=3,
        noninferiority_margin=0.0,
    )
    ctl = AutoCampaignController(campaign, AutoCampaignSchedule(shadow_pairs=1, experiment_pairs=1, holdout_pairs=1))
    ctl.record_pair(incumbent=_ok(0.1), candidate=_ok(0.01))
    ctl.record_pair(incumbent=_ok(0.1), candidate=_ok(0.01))
    ctl.record_pair(
        incumbent=_ok(0.1),
        candidate=OutcomeSample(verified=False, false_completion=True, cost_usd=0.01),
    )
    assert campaign.state is CampaignState.REJECTED
