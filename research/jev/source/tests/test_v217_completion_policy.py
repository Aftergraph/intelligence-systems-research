from __future__ import annotations

from types import SimpleNamespace

from jev_engineering.agent import CodingAgent
from jev_engineering.tools import RepoTools
from jev_engineering.types import DoneVerdict, SafetyDecision, ToolCall


class _DecisionSpy:
    def __init__(self) -> None:
        self.safety_calls = 0
        self.done_calls = 0

    def safe_to_run(self, *, task: str, command: str, policy: dict) -> SafetyDecision:
        self.safety_calls += 1
        return SafetyDecision("confirm", 0.0, 0.9, "spy-confirm")

    def done(self, *, task: str, evidence: dict) -> DoneVerdict:
        self.done_calls += 1
        return DoneVerdict(False, 0.4, 0.9, "spy-not-done")


def test_repo_local_write_auto_allow_is_explicit_and_deterministic(tmp_path) -> None:
    spy = _DecisionSpy()
    fake = SimpleNamespace(
        tools=RepoTools(tmp_path, command_mode="verify_only"),
        policy={"repo_local_write_auto_allow": True},
        decisions=spy,
    )
    call = ToolCall("c1", "write_file", {"path": "solution.py", "content": "x = 1\n"})
    verdict = CodingAgent._gate_action(fake, "repair fixture", call)
    assert verdict.action == "allow"
    assert spy.safety_calls == 0


def test_repo_local_write_without_opt_in_still_uses_typed_safety(tmp_path) -> None:
    spy = _DecisionSpy()
    fake = SimpleNamespace(
        tools=RepoTools(tmp_path, command_mode="verify_only"),
        policy={},
        decisions=spy,
    )
    call = ToolCall("c1", "replace_text", {"path": "solution.py", "old": "x", "new": "y"})
    (tmp_path / "solution.py").write_text("x = 1\n")
    verdict = CodingAgent._gate_action(fake, "repair fixture", call)
    assert verdict.action == "confirm"
    assert spy.safety_calls == 1


def test_authoritative_verifier_can_terminally_accept_fresh_exit_zero() -> None:
    spy = _DecisionSpy()
    fake = SimpleNamespace(policy={"authoritative_verifier": True}, decisions=spy)
    verdict = CodingAgent._completion_verdict(
        fake,
        task="repair fixture",
        evidence={"verification_exit_code": 0, "evidence_fresh": True},
    )
    assert verdict.verified is True
    assert verdict.done_probability == 1.0
    assert verdict.judgeable_probability == 1.0
    assert spy.done_calls == 0


def test_authoritative_verifier_never_accepts_stale_or_failing_evidence() -> None:
    for evidence in (
        {"verification_exit_code": 1, "evidence_fresh": True},
        {"verification_exit_code": 0, "evidence_fresh": False},
    ):
        spy = _DecisionSpy()
        fake = SimpleNamespace(policy={"authoritative_verifier": True}, decisions=spy)
        verdict = CodingAgent._completion_verdict(fake, task="repair fixture", evidence=evidence)
        assert verdict.verified is False
        assert spy.done_calls == 1
