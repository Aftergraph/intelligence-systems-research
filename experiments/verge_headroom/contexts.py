from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

from experiments.verge.models import stable_hash
from experiments.verge_repertoire.contexts import MissionContext

_CONTEXTS_PATH = Path(__file__).with_name("contexts.json")


def load_contexts(path: Path | None = None) -> tuple[MissionContext, ...]:
    target = path or _CONTEXTS_PATH
    raw = json.loads(target.read_text(encoding="utf-8"))
    contexts = tuple(MissionContext(**item) for item in raw)
    ids = [c.context_id for c in contexts]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate context_id")
    if {c.split for c in contexts} != {"TRAIN", "DEVELOPMENT", "HELD_OUT"}:
        raise ValueError("manifest must contain TRAIN, DEVELOPMENT and HELD_OUT")
    return contexts


def context_manifest_hash(contexts: tuple[MissionContext, ...]) -> str:
    return stable_hash(tuple(asdict(c) for c in contexts))
