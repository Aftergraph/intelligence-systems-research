from __future__ import annotations

from jev_engineering.decisions import DecisionEngine, HeuristicDecisionBackend


def test_heuristic_backend_is_conservative_for_destructive_commands() -> None:
    engine = DecisionEngine(HeuristicDecisionBackend())
    result = engine.safe_to_run(task="cleanup", command="git reset --hard HEAD")
    assert result.action == "block"


def test_heuristic_done_never_verifies_failed_exit_code() -> None:
    engine = DecisionEngine(HeuristicDecisionBackend())
    result = engine.done(task="fix", evidence={"verification_exit_code": 1, "verification_output": "1 failed"})
    assert result.verified is False
