from experiments.runtime_acceleration.runners.mission_bench import run_mission


class Treatment:
    def run(self, mission):
        return {
            "answer": "looks done",
            "tool_calls": 3,
            "browser_operations": 1,
            "model_input_tokens": 100,
            "model_output_tokens": 20,
            "provider_cost_usd": 0.01,
        }


class Verifier:
    def __init__(self, verified):
        self.verified = verified

    def verify(self, mission, execution):
        return {"verified": self.verified, "reason": "acceptance criteria"}


def test_runner_completion_is_not_verified_without_verifier_pass():
    result = run_mission({"id": "m1"}, Treatment(), Verifier(False), condition="B")
    assert result.runner_completed is True
    assert result.verified_mission_success is False
    assert result.verifier["verified"] is False


def test_mission_result_persists_treatment_counts_tokens_and_cost():
    result = run_mission({"id": "m1"}, Treatment(), Verifier(True), condition="D")
    assert result.condition == "D"
    assert result.verified_mission_success is True
    assert result.tool_calls == 3
    assert result.browser_operations == 1
    assert result.model_input_tokens == 100
    assert result.model_output_tokens == 20
    assert result.provider_cost_usd == 0.01
    assert result.mission_wall_clock_ms >= 0
