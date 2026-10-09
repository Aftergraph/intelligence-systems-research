from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IslandMember:
    candidate_id: str
    origin_island: str


@dataclass(frozen=True)
class IslandState:
    name: str
    members: tuple[IslandMember, ...]


def migrate_elites(islands: list[IslandState]) -> list[IslandState]:
    if len(islands) < 2:
        return list(islands)
    additions: dict[str, list[IslandMember]] = {island.name: [] for island in islands}
    for index, island in enumerate(islands):
        if not island.members:
            continue
        target = islands[(index + 1) % len(islands)]
        additions[target.name].append(island.members[0])
    return [
        IslandState(island.name, island.members + tuple(additions[island.name]))
        for island in islands
    ]
