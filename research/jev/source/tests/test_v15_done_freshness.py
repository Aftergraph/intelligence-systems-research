from jev_engineering.decisions import DecisionEngine
from jev_engineering.local_decisions import LocalDecisionBackend


def test_done_fails_closed_when_evidence_freshness_field_is_missing():
    engine = DecisionEngine(LocalDecisionBackend())
    verdict = engine.done(task="fix it", evidence={"verification_exit_code": 0, "verification_output": "ok"})
    assert verdict.verified is False
    assert "fresh" in verdict.reason.lower() or "exit=" in verdict.reason.lower()
