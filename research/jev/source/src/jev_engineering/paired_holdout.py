from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from .campaign_runtime import BenchmarkCostModel
from .evidence_campaign import EvidenceCampaignPolicy, evaluate_evidence_campaign

_REQUIRED_METRICS = (
    "completion_claims",
    "false_completion_claims",
    "provider_input_tokens",
    "provider_output_tokens",
    "decision_input_tokens",
    "decision_output_tokens",
    "wall_time_ms",
)
_PHASES = {"shadow", "experiment", "holdout"}


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PairedMission:
    """One preregistered mission pair.

    ``phase`` is intentionally not exposed to condition callbacks. Both conditions receive
    the same case identity and immutable payload digest so a candidate cannot be promoted
    from a different workload than the incumbent.
    """

    case_id: str
    repeat: int
    phase: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id must be non-empty")
        if self.repeat <= 0:
            raise ValueError("repeat must be positive")
        if self.phase not in _PHASES:
            raise ValueError("phase must be shadow, experiment, or holdout")

    @property
    def payload_sha256(self) -> str:
        return _canonical_hash(dict(self.payload))


@dataclass(frozen=True, slots=True)
class PairedMissionInput:
    case_id: str
    repeat: int
    payload: Mapping[str, Any]
    payload_sha256: str


@dataclass(frozen=True, slots=True)
class PairedCampaignExecution:
    records: tuple[dict[str, Any], ...]
    pair_execution_order: tuple[tuple[str, str], ...]
    shadow_pairs: int
    experiment_pairs: int
    holdout_pairs: int
    seed: int
    live_provider_measurement: bool

    def evaluate(
        self,
        *,
        incumbent_condition: str,
        candidate_condition: str,
        cost_model: BenchmarkCostModel,
        policy: EvidenceCampaignPolicy | None = None,
    ) -> dict[str, Any]:
        return evaluate_evidence_campaign(
            self.records,
            incumbent_condition=incumbent_condition,
            candidate_condition=candidate_condition,
            cost_model=cost_model,
            shadow_pairs=self.shadow_pairs,
            experiment_pairs=self.experiment_pairs,
            holdout_pairs=self.holdout_pairs,
            policy=policy,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "records": list(self.records),
            "pair_execution_order": [list(order) for order in self.pair_execution_order],
            "phase_allocation": {
                "shadow": self.shadow_pairs,
                "experiment": self.experiment_pairs,
                "holdout": self.holdout_pairs,
            },
            "seed": self.seed,
            "live_provider_measurement": self.live_provider_measurement,
            "truth_boundary": (
                "execution records are paired telemetry; performance promotion requires the reserved "
                "holdout evaluator and does not grant execution authority"
            ),
        }


class PairedHoldoutCampaignRunner:
    """Run identical paired missions with deterministic counterbalanced condition order.

    The runner deliberately has no promotion side effect. It only produces paired records
    that can be evaluated by the existing evidence-grade holdout gate.
    """

    def __init__(
        self,
        *,
        incumbent_condition: str,
        candidate_condition: str,
        seed: int = 20260925,
    ) -> None:
        if not incumbent_condition.strip() or not candidate_condition.strip():
            raise ValueError("condition names must be non-empty")
        if incumbent_condition == candidate_condition:
            raise ValueError("incumbent and candidate conditions must differ")
        self.incumbent_condition = incumbent_condition
        self.candidate_condition = candidate_condition
        self.seed = seed

    def _order(self, mission: PairedMission) -> tuple[str, str]:
        digest = hashlib.sha256(
            f"{self.seed}:{mission.repeat}:{mission.case_id}".encode("utf-8")
        ).digest()
        conditions = (self.incumbent_condition, self.candidate_condition)
        return conditions if digest[0] % 2 == 0 else conditions[::-1]

    @staticmethod
    def _validate_schedule(missions: Sequence[PairedMission]) -> tuple[int, int, int]:
        if not missions:
            raise ValueError("at least one paired mission is required")
        keys: set[tuple[int, str]] = set()
        seen_phase_rank = -1
        rank = {"shadow": 0, "experiment": 1, "holdout": 2}
        counts = {"shadow": 0, "experiment": 0, "holdout": 0}
        for mission in sorted(missions, key=lambda m: (m.repeat, m.case_id)):
            key = (mission.repeat, mission.case_id)
            if key in keys:
                raise ValueError("duplicate paired mission key")
            keys.add(key)
            phase_rank = rank[mission.phase]
            if phase_rank < seen_phase_rank:
                raise ValueError("campaign phases must be contiguous in repeat/case sort order")
            seen_phase_rank = max(seen_phase_rank, phase_rank)
            counts[mission.phase] += 1
        if counts["holdout"] < 1:
            raise ValueError("campaign requires at least one holdout pair")
        return counts["shadow"], counts["experiment"], counts["holdout"]

    @staticmethod
    def _normalize_record(
        *,
        mission: PairedMission,
        condition: str,
        execution_order: int,
        raw: Mapping[str, Any],
    ) -> dict[str, Any]:
        status = str(raw.get("status") or "")
        if not status:
            raise ValueError("condition callback must return status")
        metrics = dict(raw.get("metrics") or {})
        missing = [key for key in _REQUIRED_METRICS if key not in metrics]
        if missing:
            raise ValueError(f"condition callback missing metrics: {', '.join(missing)}")
        for key in _REQUIRED_METRICS:
            value = metrics[key]
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                raise ValueError(f"metric {key} must be a non-negative number")
        if metrics["false_completion_claims"] > metrics["completion_claims"]:
            raise ValueError("false_completion_claims cannot exceed completion_claims")

        record = dict(raw)
        record.update(
            {
                "condition": condition,
                "case_id": mission.case_id,
                "repeat": mission.repeat,
                "phase": mission.phase,
                "payload_sha256": mission.payload_sha256,
                "pair_execution_order": execution_order,
                "metrics": metrics,
            }
        )
        return record

    def run(
        self,
        *,
        missions: Sequence[PairedMission],
        run_condition: Callable[[PairedMissionInput, str], Mapping[str, Any]],
        live_provider_measurement: bool = False,
    ) -> PairedCampaignExecution:
        shadow_pairs, experiment_pairs, holdout_pairs = self._validate_schedule(missions)
        records: list[dict[str, Any]] = []
        orders: list[tuple[str, str]] = []
        for mission in sorted(missions, key=lambda m: (m.repeat, m.case_id)):
            mission_input = PairedMissionInput(
                case_id=mission.case_id,
                repeat=mission.repeat,
                payload=dict(mission.payload),
                payload_sha256=mission.payload_sha256,
            )
            order = self._order(mission)
            orders.append(order)
            pair_records = []
            for execution_order, condition in enumerate(order, start=1):
                raw = run_condition(mission_input, condition)
                pair_records.append(
                    self._normalize_record(
                        mission=mission,
                        condition=condition,
                        execution_order=execution_order,
                        raw=raw,
                    )
                )
            if len({row["payload_sha256"] for row in pair_records}) != 1:
                raise AssertionError("paired payload identity violated")
            records.extend(pair_records)
        return PairedCampaignExecution(
            records=tuple(records),
            pair_execution_order=tuple(orders),
            shadow_pairs=shadow_pairs,
            experiment_pairs=experiment_pairs,
            holdout_pairs=holdout_pairs,
            seed=self.seed,
            live_provider_measurement=live_provider_measurement,
        )
