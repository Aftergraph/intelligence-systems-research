from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .learning import LearningCandidate, LearningRatchet, LearningState, PromotionPolicy
from .statistics import wilson_interval


class CampaignState(str, Enum):
    SHADOW = "shadow"
    EXPERIMENT = "experiment"
    HOLDOUT = "holdout"
    PROMOTED = "promoted"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class OutcomeSample:
    verified: bool
    false_completion: bool
    cost_usd: float


@dataclass(slots=True)
class LearningCampaign:
    """Bounded online campaign with statistical promotion and post-promotion guardrails."""

    candidate: LearningCandidate
    policy: PromotionPolicy
    min_holdout_trials: int = 20
    noninferiority_margin: float = 0.02
    max_post_promotion_fcr: float = 0.0
    state: CampaignState = CampaignState.SHADOW
    incumbent: list[OutcomeSample] = field(default_factory=list)
    candidate_samples: list[OutcomeSample] = field(default_factory=list)
    post_promotion: list[OutcomeSample] = field(default_factory=list)

    def record_pair(self, *, incumbent: OutcomeSample, candidate: OutcomeSample) -> None:
        if self.state not in {CampaignState.SHADOW, CampaignState.EXPERIMENT, CampaignState.HOLDOUT}:
            raise RuntimeError("campaign no longer accepts paired pre-promotion samples")
        self.incumbent.append(incumbent)
        self.candidate_samples.append(candidate)

    def advance(self, state: CampaignState) -> None:
        allowed = {
            CampaignState.SHADOW: {CampaignState.EXPERIMENT, CampaignState.REJECTED},
            CampaignState.EXPERIMENT: {CampaignState.HOLDOUT, CampaignState.REJECTED},
            CampaignState.HOLDOUT: {CampaignState.PROMOTED, CampaignState.REJECTED},
            CampaignState.PROMOTED: {CampaignState.QUARANTINED},
            CampaignState.QUARANTINED: set(),
            CampaignState.REJECTED: set(),
        }
        if state not in allowed[self.state]:
            raise RuntimeError(f"illegal campaign transition {self.state.value} -> {state.value}")
        if state is CampaignState.PROMOTED:
            decision = self.promotion_decision()
            if not decision["promote"]:
                raise RuntimeError("promotion gate failed: " + "; ".join(decision["reasons"]))
        self.state = state

    def promotion_decision(self) -> dict[str, Any]:
        reasons: list[str] = []
        if len(self.candidate_samples) < self.min_holdout_trials:
            reasons.append("insufficient holdout trials")
            return {"promote": False, "reasons": reasons}
        inc_success = sum(s.verified for s in self.incumbent)
        cand_success = sum(s.verified for s in self.candidate_samples)
        inc_ci = wilson_interval(inc_success, len(self.incumbent))
        cand_ci = wilson_interval(cand_success, len(self.candidate_samples))
        if cand_ci.lower + self.noninferiority_margin < inc_ci.lower:
            reasons.append("candidate Wilson lower bound violates non-inferiority margin")
        cand_fcr = sum(s.false_completion for s in self.candidate_samples) / len(self.candidate_samples)
        if cand_fcr > self.policy.max_fcr:
            reasons.append("candidate FCR exceeds policy")
        inc_verified = max(1, inc_success)
        cand_verified = max(1, cand_success)
        inc_cpvo = sum(s.cost_usd for s in self.incumbent) / inc_verified
        cand_cpvo = sum(s.cost_usd for s in self.candidate_samples) / cand_verified
        if self.policy.require_lower_cpvo and cand_cpvo >= inc_cpvo:
            reasons.append("candidate CPVO is not lower")
        return {
            "promote": not reasons,
            "reasons": reasons,
            "incumbent_vsr": inc_success / len(self.incumbent),
            "candidate_vsr": cand_success / len(self.candidate_samples),
            "incumbent_vsr_ci": [inc_ci.lower, inc_ci.upper],
            "candidate_vsr_ci": [cand_ci.lower, cand_ci.upper],
            "candidate_fcr": cand_fcr,
            "incumbent_cpvo": inc_cpvo,
            "candidate_cpvo": cand_cpvo,
        }

    def record_post_promotion(self, sample: OutcomeSample) -> bool:
        if self.state is not CampaignState.PROMOTED:
            raise RuntimeError("candidate is not promoted")
        self.post_promotion.append(sample)
        if sample.false_completion:
            self.state = CampaignState.QUARANTINED
            return False
        fcr = sum(s.false_completion for s in self.post_promotion) / len(self.post_promotion)
        if fcr > self.max_post_promotion_fcr:
            self.state = CampaignState.QUARANTINED
            return False
        return True
