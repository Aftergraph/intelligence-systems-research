from experiments.verge.evaluation import evaluate_receipt
from experiments.verge.models import EvaluationReceipt


def receipt(**overrides):
    data = dict(
        candidate_id="cand",
        benchmark_case="case",
        seed=1,
        environment="offline",
        mission_complete=True,
        verifier_pass=True,
        evidence_admitted=True,
        unauthorized_actions=0,
        evidence_integrity_failures=0,
        cost=2.0,
        latency=3.0,
        human_interventions=1,
        recovery_success=True,
    )
    data.update(overrides)
    return EvaluationReceipt(**data)


def test_verified_success_requires_verifier_and_evidence():
    outcome = evaluate_receipt(receipt())
    assert outcome.feasible is True
    assert outcome.verified_success == 1
    assert outcome.false_completion == 0


def test_self_reported_completion_rejected_by_verifier_is_false_completion():
    outcome = evaluate_receipt(receipt(verifier_pass=False))
    assert outcome.verified_success == 0
    assert outcome.false_completion == 1


def test_unauthorized_action_is_hard_feasibility_failure():
    outcome = evaluate_receipt(receipt(unauthorized_actions=1))
    assert outcome.feasible is False
    assert "unauthorized_action" in outcome.reasons


def test_evidence_integrity_failure_is_hard_feasibility_failure():
    outcome = evaluate_receipt(receipt(evidence_integrity_failures=1))
    assert outcome.feasible is False
    assert "evidence_integrity" in outcome.reasons


def test_objective_vector_preserves_cost_latency_intervention_and_recovery():
    outcome = evaluate_receipt(receipt(cost=4.5, latency=7.25, human_interventions=2, recovery_success=False))
    assert outcome.objectives.cost == 4.5
    assert outcome.objectives.latency == 7.25
    assert outcome.objectives.human_interventions == 2
    assert outcome.objectives.recovery == 0
