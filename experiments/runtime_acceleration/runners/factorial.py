from __future__ import annotations

import random


def build_counterbalanced_schedule(missions: list[str], conditions: list[str], seed: int) -> list[dict]:
    """Create a seeded within-mission schedule containing every condition once."""
    if not missions or not conditions:
        raise ValueError("missions and conditions must be non-empty")
    rng = random.Random(seed)
    schedule = []
    for mission in missions:
        local = list(conditions)
        rng.shuffle(local)
        schedule.extend({"mission": mission, "condition": condition} for condition in local)
    return schedule
