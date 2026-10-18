from __future__ import annotations

from dataclasses import dataclass

from .learning_campaign import CampaignState, LearningCampaign, OutcomeSample


@dataclass(frozen=True, slots=True)
class AutoCampaignSchedule:
    shadow_pairs: int = 20
    experiment_pairs: int = 20
    holdout_pairs: int = 20

    def __post_init__(self) -> None:
        if min(self.shadow_pairs, self.experiment_pairs, self.holdout_pairs) < 1:
            raise ValueError("automatic campaign phase sizes must be >= 1")


class AutoCampaignController:
    """Deterministic phase driver around LearningCampaign.

    It automates phase progression only. It does not manufacture candidate outcomes,
    grant authority, or bypass the campaign's statistical promotion gate.
    """

    def __init__(self, campaign: LearningCampaign, schedule: AutoCampaignSchedule | None = None) -> None:
        self.campaign = campaign
        self.schedule = schedule or AutoCampaignSchedule()
        self.phase_counts = {"shadow": 0, "experiment": 0, "holdout": 0}

    def record_pair(self, *, incumbent: OutcomeSample, candidate: OutcomeSample) -> CampaignState:
        state = self.campaign.state
        if state not in {CampaignState.SHADOW, CampaignState.EXPERIMENT, CampaignState.HOLDOUT}:
            raise RuntimeError("automatic campaign is not accepting pre-promotion samples")
        self.campaign.record_pair(incumbent=incumbent, candidate=candidate)
        self.phase_counts[state.value] += 1
        if state is CampaignState.SHADOW and self.phase_counts["shadow"] >= self.schedule.shadow_pairs:
            self.campaign.advance(CampaignState.EXPERIMENT)
        elif state is CampaignState.EXPERIMENT and self.phase_counts["experiment"] >= self.schedule.experiment_pairs:
            self.campaign.advance(CampaignState.HOLDOUT)
        elif state is CampaignState.HOLDOUT and self.phase_counts["holdout"] >= self.schedule.holdout_pairs:
            decision = self.campaign.promotion_decision()
            self.campaign.advance(CampaignState.PROMOTED if decision["promote"] else CampaignState.REJECTED)
        return self.campaign.state

    def record_post_promotion(self, sample: OutcomeSample) -> CampaignState:
        self.campaign.record_post_promotion(sample)
        return self.campaign.state
