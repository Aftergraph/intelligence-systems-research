from experiments.system_one_acceleration.protocol import (
    DecisionPolicy,
    route_system_one_decision,
)


def _route(**overrides):
    args = {
        "decision_type": "continue_loop",
        "answer_kind": "noul",
        "answer_value": 0.98,
        "reported_confidence": None,
        "transport_ok": True,
        "schema_ok": True,
        "authority_sensitive_ambiguity": False,
        "evidence_conflict": False,
        "policy": DecisionPolicy(confidence_threshold=0.90),
    }
    args.update(overrides)
    return route_system_one_decision(**args)


def test_high_certainty_noul_is_advisory_accept():
    result = _route()
    assert result.decision == "accept"
    assert result.effective_confidence == 0.96
    assert result.authority_bypassed is False


def test_noul_near_half_falls_back():
    result = _route(answer_value=0.55)
    assert result.decision == "fallback"
    assert result.fallback_reason == "below_confidence_threshold"


def test_choice_uses_reported_confidence():
    result = _route(
        decision_type="route_model",
        answer_kind="choice",
        answer_value="fast",
        reported_confidence=0.94,
    )
    assert result.decision == "accept"
    assert result.effective_confidence == 0.94


def test_transport_failure_falls_back_before_confidence():
    result = _route(transport_ok=False)
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


def test_invalid_noul_probability_falls_back():
    result = _route(answer_value=1.2)
    assert result.decision == "fallback"
    assert result.fallback_reason == "invalid_confidence"


def test_boolean_is_not_accepted_as_noul_probability():
    result = _route(answer_value=True)
    assert result.decision == "fallback"
    assert result.fallback_reason == "invalid_confidence"


def test_choice_without_reported_confidence_falls_back():
    result = _route(
        decision_type="route_model",
        answer_kind="choice",
        answer_value="fast",
        reported_confidence=None,
    )
    assert result.decision == "fallback"
    assert result.fallback_reason == "invalid_confidence"


def test_policy_rejects_invalid_threshold():
    try:
        DecisionPolicy(confidence_threshold=1.01)
    except ValueError:
        return
    raise AssertionError("invalid confidence threshold must fail closed")
