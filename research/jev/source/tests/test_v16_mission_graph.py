from __future__ import annotations

import pytest

from jev_engineering.mission_graph import MissionGraph, MissionNode, NodeState


def test_speculative_node_cannot_verify_before_dependency() -> None:
    graph = MissionGraph([
        MissionNode('a'),
        MissionNode('b', dependencies=('a',), speculative_allowed=True),
    ])
    assert graph.nodes['a'].state is NodeState.READY
    assert graph.nodes['b'] in graph.speculative_candidates()
    graph.begin_speculation('b')
    with pytest.raises(RuntimeError):
        graph.mark_verified('b')
    graph.mark_verified('a')
    graph.mark_verified('b')
    graph.commit('b')
    assert graph.nodes['b'].state is NodeState.COMMITTED


def test_failure_invalidates_descendants_transitively() -> None:
    graph = MissionGraph([
        MissionNode('a'),
        MissionNode('b', dependencies=('a',), speculative_allowed=True),
        MissionNode('c', dependencies=('b',), speculative_allowed=True),
    ])
    graph.fail('a')
    assert graph.nodes['b'].state is NodeState.INVALIDATED
    assert graph.nodes['c'].state is NodeState.INVALIDATED


def test_cycles_rejected() -> None:
    with pytest.raises(ValueError):
        MissionGraph([MissionNode('a', ('b',)), MissionNode('b', ('a',))])
