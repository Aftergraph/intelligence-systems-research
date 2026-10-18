from __future__ import annotations

from pathlib import Path
import json

from .evaluation import EvaluationOutcome, ObjectiveVector, evaluate_receipt
from .models import EvaluationReceipt, PolicyGenome, stable_hash


_CASES_PATH = Path(__file__).with_name("cases") / "s2_cases.json"


def load_cases(path: Path | None = None) -> tuple[dict, ...]:
    target = path or _CASES_PATH
    return tuple(json.loads(target.read_text(encoding="utf-8")))


def benchmark_manifest_hash(cases: tuple[dict, ...]) -> str:
    return stable_hash(cases)


def _case_receipt(genome: PolicyGenome, case: dict, seed: int) -> EvaluationReceipt:
    has_verify = "verify" in genome.routing_policy
    claims_complete = "execute" in genome.routing_policy
    recovery_ok = (not case["recovery"]) or (genome.retry_ceiling >= case["min_retries"] and has_verify)
    verifier_pass = (
        claims_complete
        and has_verify
        and genome.verification_depth >= case["min_verification"]
        and genome.confidence_threshold >= case["min_confidence"]
        and genome.retry_ceiling >= case["min_retries"]
        and recovery_ok
    )
    authority_violation = int(
        case["risk"] == "authority"
        and (
            genome.verification_depth < case["min_verification"]
            or genome.confidence_threshold < case["min_confidence"]
        )
        and claims_complete
    )
    evidence_failure = int(claims_complete and not has_verify)
    cost = case["base_cost"] * (
        1.0
        + 0.12 * genome.verification_depth
        + 0.08 * genome.retry_ceiling
        + 0.05 * genome.parallelism
    )
    latency = case["base_latency"] * (
        1.0 + 0.15 * genome.verification_depth + 0.08 * genome.retry_ceiling
    ) / (genome.parallelism ** 0.5)
    interventions = int(genome.confidence_threshold < case["min_confidence"])
    return EvaluationReceipt(
        candidate_id=genome.identity,
        benchmark_case=case["id"],
        seed=seed,
        environment="S2_OFFLINE_DETERMINISTIC",
        mission_complete=claims_complete,
        verifier_pass=verifier_pass,
        evidence_admitted=has_verify,
        unauthorized_actions=authority_violation,
        evidence_integrity_failures=evidence_failure,
        cost=cost,
        latency=latency,
        human_interventions=interventions,
        recovery_success=recovery_ok,
    )


def evaluate_policy(genome: PolicyGenome, cases: tuple[dict, ...], seed: int) -> EvaluationOutcome:
    outcomes = [evaluate_receipt(_case_receipt(genome, case, seed)) for case in cases]
    reasons = tuple(sorted({reason for outcome in outcomes for reason in outcome.reasons}))
    objectives = ObjectiveVector(
        verified_success=sum(outcome.objectives.verified_success for outcome in outcomes),
        false_completion=sum(outcome.objectives.false_completion for outcome in outcomes),
        unauthorized_actions=sum(outcome.objectives.unauthorized_actions for outcome in outcomes),
        cost=sum(outcome.objectives.cost for outcome in outcomes),
        latency=sum(outcome.objectives.latency for outcome in outcomes),
        human_interventions=sum(outcome.objectives.human_interventions for outcome in outcomes),
        recovery=sum(outcome.objectives.recovery for outcome in outcomes),
    )
    return EvaluationOutcome(
        feasible=all(outcome.feasible for outcome in outcomes),
        reasons=reasons,
        verified_success=objectives.verified_success,
        false_completion=objectives.false_completion,
        objectives=objectives,
    )
