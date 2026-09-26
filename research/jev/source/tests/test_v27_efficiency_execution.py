from jev_engineering.context_compiler import ContextCandidate
from jev_engineering.efficiency_execution import (
    EmpiricalEfficiencyExecutionEngine, EfficiencyExecutionPolicy, ExecutionAttempt,
)
from jev_engineering.system_efficiency import RetryCandidate


def ctx():
    return [
        ContextCandidate("goal", "g", 1000, relevance=1, information_gain=1),
        ContextCandidate("code", "c", 2000, relevance=.95, information_gain=1),
        ContextCandidate("noise", "n", 9000, relevance=.01, information_gain=.1),
    ]


def test_verified_cheap_path_skips_frontier():
    calls=[]
    r=EmpiricalEfficiencyExecutionEngine().run(
        mission_id="m1", context=ctx(), policy=EfficiencyExecutionPolicy(required_vsr=.95),
        cheap_attempt=lambda keys: ExecutionAttempt("cheap", True, .97, evidence_ids=("proof:1",)),
        frontier_attempt=lambda keys, retry: calls.append(1),
    )
    assert r.verified and r.frontier_calls == 0 and r.frontier_tokens == 0
    assert not calls
    assert r.selected_context_tokens < r.candidate_context_tokens


def test_unverified_cheap_path_escalates_to_frontier():
    r=EmpiricalEfficiencyExecutionEngine().run(
        mission_id="m2", context=ctx(), policy=EfficiencyExecutionPolicy(frontier_token_budget=5000),
        cheap_attempt=lambda keys: ExecutionAttempt("cheap", False, .99),
        frontier_attempt=lambda keys, retry: ExecutionAttempt("frontier", True, .99, 2500, 500, .03, ("proof:f",)),
    )
    assert r.verified and r.frontier_calls == 1 and r.frontier_tokens == 3000


def test_retry_gate_executes_only_admitted_retries():
    seen=[]
    def frontier(keys, retry):
        seen.append(retry)
        return ExecutionAttempt("frontier" if retry == 0 else "frontier_retry", retry == 2, .9, 1000, 500)
    r=EmpiricalEfficiencyExecutionEngine().run(
        mission_id="m3", context=ctx(), policy=EfficiencyExecutionPolicy(frontier_token_budget=6000),
        cheap_attempt=lambda keys: ExecutionAttempt("cheap", False, .5), frontier_attempt=frontier,
        retry_candidates=[RetryCandidate(1,.05,1500), RetryCandidate(2,.03,1500), RetryCandidate(3,.001,1500)],
    )
    assert seen == [0,1,2]
    assert r.verified and r.stop_reason == "frontier_retry_verified"


def test_budget_is_fail_closed():
    r=EmpiricalEfficiencyExecutionEngine().run(
        mission_id="m4", context=ctx(), policy=EfficiencyExecutionPolicy(frontier_token_budget=1000),
        cheap_attempt=lambda keys: ExecutionAttempt("cheap", False, .5),
        frontier_attempt=lambda keys, retry: ExecutionAttempt("frontier", True, .99, 1200, 200),
    )
    assert not r.verified and r.frontier_calls == 0 and r.stop_reason == "frontier_budget_exceeded"
