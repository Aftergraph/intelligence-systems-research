from experiments.system_one_acceleration.protocol import (
    DecisionPolicy,
    route_system_one_decision,
)


def _route(**overrides):
    args = {
        "decision_type": "continue_loop",
        "answer_kind": "noul",
        "confidence": 0.95,
        "transport_ok": True,
        "schema_ok": True,
        "authority_sensitive_ambiguity": False,
        "evidence_conflict": False,
        "policy": DecisionPolicy(confidence_threshold=0.90),
    }
    args.update(overrides)
    return route_system_one_decision(**args)


def test_high_confidence_eligible_decision_is_advisory_accept():
    result = _route()
    assert result.decision == "accept"
    assert result.fallback_used is False
    assert result.authority_bypassed is False


def test_low_confidence_falls_back():
    result = _route(confidence=0.89)
    assert result.decision == "fallback"
    assert result.fallback_reason == "below_confidence_threshold"


def test_transport_failure_falls_back_before_confidence():
    result = _route(transport_ok=False, confidence=0.99)
    assert result.decision == "fallback"
    assert result.fallback_reason == "transport_failure"


def test_schema_failure_falls_back():
    result = _route(schema_ok=False)
    assert result.decision == "fallback"
    assert result.fallback_reason == "schema_failure"


def test_authority_ambiguity_escalates_and_never_bypasses():
    result = _route(authority_sensitive_ambiguity=True)
    assert result.decision == "escalate"
    assert result.fallback_used is True
    assert result.authority_bypassed is False


def test_evidence_conflict_escalates():
    result = _route(evidence_conflict=True)
    assert result.decision == "escalate"
    assert result.fallback_reason == "evidence_conflict"


def test_ineligible_open_ended_reasoning_falls_back():
    result = _route(decision_type="generate_patch")
    assert result.decision == "fallback"
    assert result.fallback_reason == "ineligible_decision_type"


def test_invalid_probability_falls_back():
    result = _route(confidence=1.2)
    assert result.decision == "fallback"
    assert result.fallback_reason == "invalid_confidence"


def test_policy_rejects_invalid_threshold():
    try:
        DecisionPolicy(confidence_threshold=1.01)
    except ValueError:
        return
    raise AssertionError("invalid confidence threshold must fail closed")
