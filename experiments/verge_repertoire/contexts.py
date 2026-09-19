from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json

from experiments.verge.models import stable_hash


_CONTEXTS_PATH = Path(__file__).with_name("contexts.json")


@dataclass(frozen=True)
class MissionContext:
    context_id: str
    split: str
    risk_class: int
    failure_pressure: float
    latency_pressure: float
    cost_pressure: float
    min_verification: int
    min_confidence: float
    min_retries: int
    base_cost: float
    base_latency: float

    def descriptor(self) -> tuple[float, float, float, float]:
        return (
            float(self.risk_class) / 2.0,
            float(self.failure_pressure),
            float(self.latency_pressure),
            float(self.cost_pressure),
        )


def load_contexts(path: Path | None = None) -> tuple[MissionContext, ...]:
    target = path or _CONTEXTS_PATH
    raw = json.loads(target.read_text(encoding="utf-8"))
    contexts = tuple(MissionContext(**item) for item in raw)
    ids = [context.context_id for context in contexts]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate context_id")
    allowed = {"TRAIN", "DEVELOPMENT", "HELD_OUT"}
    if any(context.split not in allowed for context in contexts):
        raise ValueError("invalid context split")
    return contexts


def context_manifest_hash(contexts: tuple[MissionContext, ...]) -> str:
    return stable_hash(tuple(asdict(context) for context in contexts))
