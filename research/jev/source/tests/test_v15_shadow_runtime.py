from pathlib import Path

from jev_engineering.shadow_runtime import ShadowDecisionEngine, PromotionRegistry
from jev_engineering.types import CandidateFile, SafetyDecision, DoneVerdict, ModelProfile
from jev_engineering.learning import LearningCandidate, LearningState, PromotionPolicy


class StubDecisions:
    def __init__(self, *, suffix="", fail_station=None):
        self.suffix = suffix
        self.fail_station = fail_station
        self.calls = 0

    def _maybe(self, station):
        self.calls += 1
        if self.fail_station == station:
            raise RuntimeError(f"shadow boom at {station}")

    def scope(self, *, task, candidates, top_k=8):
        self._maybe("scope")
        return [CandidateFile(candidates[0].path, candidates[0].excerpt, 4.0, 0.99)]

    def choose_model(self, task, models, *, frontier_required=True, state=None):
        self._maybe("choose_model")
        return models[0]

    def safe_to_run(self, *, task, command, policy=None):
        self._maybe("safe_to_run")
        action = "allow" if self.suffix != "different" else "confirm"
        return SafetyDecision(action, 0.01, 0.02, "stub")

    def done(self, *, task, evidence):
        self._maybe("done")
        verified = self.suffix != "different"
        return DoneVerdict(verified, 0.95, 0.95, "stub")

    def retention(self, *, task, outputs):
        self._maybe("retention")
        return ["keep"] * len(outputs)

    def loop_probability(self, *, task, recent_actions):
        self._maybe("loop_probability")
        return 0.1

    def telemetry(self):
        return {"calls": self.calls, "input_tokens": 0, "output_tokens": 0, "latency_ms": 0.0}


def test_shadow_never_controls_incumbent_and_equivalent_path_can_observe_outcome(tmp_path: Path):
    incumbent = StubDecisions()
    candidate = StubDecisions()
    shadow = ShadowDecisionEngine(
        incumbent=incumbent,
        candidate=candidate,
        incumbent_strategy="frontier-control",
        candidate_strategy="jev-control",
        log_path=tmp_path / "shadow.jsonl",
    )

    result = shadow.safe_to_run(task="x", command="pytest")
    assert result.action == "allow"
    summary = shadow.finalize_mission(verified_outcome=True, trace_id="t1")

    assert summary.path_equivalent is True
    assert summary.candidate_outcome_observable is True
    assert summary.candidate_verified_outcome is True
    assert summary.shadow_calls == 1
    assert (tmp_path / "shadow.jsonl").exists()


def test_shadow_divergence_or_error_never_changes_incumbent_and_outcome_stays_unknown():
    incumbent = StubDecisions()
    divergent = StubDecisions(suffix="different")
    shadow = ShadowDecisionEngine(
        incumbent=incumbent,
        candidate=divergent,
        incumbent_strategy="frontier-control",
        candidate_strategy="jev-control",
    )
    result = shadow.safe_to_run(task="x", command="pytest")
    assert result.action == "allow"
    summary = shadow.finalize_mission(verified_outcome=True, trace_id="t2")
    assert summary.path_equivalent is False
    assert summary.candidate_outcome_observable is False
    assert summary.candidate_verified_outcome is None

    broken = ShadowDecisionEngine(
        incumbent=incumbent,
        candidate=StubDecisions(fail_station="safe_to_run"),
        incumbent_strategy="frontier-control",
        candidate_strategy="broken-shadow",
    )
    assert broken.safe_to_run(task="x", command="pytest").action == "allow"
    summary2 = broken.finalize_mission(verified_outcome=False, trace_id="t3")
    assert summary2.candidate_errors == 1
    assert summary2.candidate_verified_outcome is None


def test_hard_policy_promotion_registry_is_persistent_and_cannot_skip_ratchet(tmp_path: Path):
    path = tmp_path / "routes.json"
    registry = PromotionRegistry(path=path)
    policy = PromotionPolicy(
        vsr_noninferiority_margin=0.01,
        max_fcr=0.01,
        min_replay_runs=2,
        min_shadow_runs=2,
        min_experimental_runs=2,
        min_holdout_runs=4,
    )
    candidate = LearningCandidate(
        candidate_id="c1",
        decision_family="safe_to_run",
        incumbent_strategy="frontier-control",
        candidate_strategy="jev-control",
        state=LearningState.HOLDOUT_VERIFIED,
        replay_runs=2,
        shadow_runs=3,
        experimental_runs=2,
        holdout_runs=4,
        holdout_successes=4,
        incumbent_vsr=0.99,
        candidate_vsr=0.99,
        candidate_fcr=0.0,
        incumbent_cpvo=0.10,
        candidate_cpvo=0.01,
    )

    promoted = registry.promote(candidate, policy=policy)
    assert promoted.state is LearningState.PROMOTED
    assert registry.preferred("safe_to_run") == "jev-control"
    assert PromotionRegistry.load(path).preferred("safe_to_run") == "jev-control"

    insufficient = LearningCandidate(
        candidate_id="c2",
        decision_family="done",
        incumbent_strategy="frontier-control",
        candidate_strategy="jev-control",
        state=LearningState.HOLDOUT_VERIFIED,
        replay_runs=0,
        shadow_runs=0,
        experimental_runs=0,
        holdout_runs=1,
        holdout_successes=1,
        incumbent_vsr=0.99,
        candidate_vsr=0.99,
        candidate_fcr=0.0,
        incumbent_cpvo=0.10,
        candidate_cpvo=0.01,
    )
    try:
        registry.promote(insufficient, policy=policy)
    except RuntimeError as exc:
        assert "promotion policy rejected" in str(exc)
    else:
        raise AssertionError("insufficient evidence must fail closed")


def test_shadow_runtime_is_wired_into_real_agent_loop(tmp_path: Path):
    from jev_engineering.agent import CodingAgent
    from jev_engineering.decisions import DecisionEngine
    from jev_engineering.local_decisions import LocalDecisionBackend
    from jev_engineering.model_registry import ModelRegistry
    from jev_engineering.providers.mock import ScriptedProviderFactory

    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (tmp_path / "test_calc.py").write_text(
        "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n", encoding="utf-8"
    )
    incumbent = DecisionEngine(LocalDecisionBackend())
    candidate = DecisionEngine(LocalDecisionBackend())
    shadow = ShadowDecisionEngine(
        incumbent=incumbent,
        candidate=candidate,
        incumbent_strategy="local-incumbent",
        candidate_strategy="local-shadow",
        log_path=tmp_path / ".jev-one" / "shadow.jsonl",
    )
    registry = ModelRegistry.from_dict({
        "models": {
            "frontier": {
                "provider": "mock",
                "model": "scripted",
                "tier": "frontier",
                "transport": "mock",
            }
        }
    })
    provider = ScriptedProviderFactory(turns=[
        {"tool_calls": [{"id": "e1", "name": "write_file", "arguments": {"path": "calc.py", "content": "def add(a, b):\n    return a + b\n"}}]},
        {"text": "candidate complete"},
    ])
    result = CodingAgent(
        workspace=tmp_path,
        decisions=shadow,
        registry=registry,
        provider_factory=provider,
        verify_command="python -m pytest -q",
        max_turns=4,
        retention_every=0,
        loop_check_every=0,
    ).run("Fix add")
    assert result.status.value == "verified"
    assert result.metrics["shadow_calls"] >= 1
    assert result.metrics["shadow_errors"] == 0
    assert (tmp_path / ".jev-one" / "shadow.jsonl").exists()


def test_promoted_decision_family_becomes_active_only_after_registry_evidence(tmp_path: Path):
    registry = PromotionRegistry(path=tmp_path / "routes.json")
    incumbent = StubDecisions()
    candidate = StubDecisions(suffix="different")
    before = ShadowDecisionEngine(
        incumbent=incumbent,
        candidate=candidate,
        incumbent_strategy="frontier-control",
        candidate_strategy="jev-control",
        promotion_registry=registry,
    )
    assert before.safe_to_run(task="x", command="pytest").action == "allow"

    registry.register(LearningCandidate(
        candidate_id="promoted-safe",
        decision_family="safe_to_run",
        incumbent_strategy="frontier-control",
        candidate_strategy="jev-control",
        state=LearningState.PROMOTED,
        holdout_runs=10,
        holdout_successes=10,
    ))
    after = ShadowDecisionEngine(
        incumbent=StubDecisions(),
        candidate=StubDecisions(suffix="different"),
        incumbent_strategy="frontier-control",
        candidate_strategy="jev-control",
        promotion_registry=registry,
    )
    assert after.safe_to_run(task="x", command="pytest").action == "confirm"
    summary = after.finalize_mission(verified_outcome=True, trace_id="promoted")
    assert summary.candidate_outcome_observable is True
    assert summary.candidate_verified_outcome is True


def test_promoted_candidate_failure_fails_closed_instead_of_silent_fallback(tmp_path: Path):
    registry = PromotionRegistry(path=tmp_path / "routes.json")
    registry.register(LearningCandidate(
        candidate_id="promoted-safe",
        decision_family="safe_to_run",
        incumbent_strategy="frontier-control",
        candidate_strategy="jev-control",
        state=LearningState.PROMOTED,
        holdout_runs=10,
        holdout_successes=10,
    ))
    routed = ShadowDecisionEngine(
        incumbent=StubDecisions(),
        candidate=StubDecisions(fail_station="safe_to_run"),
        incumbent_strategy="frontier-control",
        candidate_strategy="jev-control",
        promotion_registry=registry,
    )
    import pytest
    with pytest.raises(RuntimeError, match="promoted decision strategy"):
        routed.safe_to_run(task="x", command="pytest")
