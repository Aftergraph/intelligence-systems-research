from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter_ns


@dataclass(frozen=True)
class MissionResult:
    mission_id: str
    condition: str
    runner_completed: bool
    verified_mission_success: bool
    mission_wall_clock_ms: float
    verifier: dict
    tool_calls: int
    browser_operations: int
    model_input_tokens: int
    model_output_tokens: int
    provider_cost_usd: float
    execution: dict


def run_mission(mission: dict, treatment, verifier, *, condition: str) -> MissionResult:
    started = perf_counter_ns()
    execution = treatment.run(mission)
    runner_completed = True
    verdict = verifier.verify(mission, execution)
    elapsed_ms = (perf_counter_ns() - started) / 1_000_000
    verified = verdict.get("verified") is True
    return MissionResult(
        mission_id=str(mission.get("id", "unknown")),
        condition=condition,
        runner_completed=runner_completed,
        verified_mission_success=verified,
        mission_wall_clock_ms=elapsed_ms,
        verifier=dict(verdict),
        tool_calls=int(execution.get("tool_calls", 0)),
        browser_operations=int(execution.get("browser_operations", 0)),
        model_input_tokens=int(execution.get("model_input_tokens", 0)),
        model_output_tokens=int(execution.get("model_output_tokens", 0)),
        provider_cost_usd=float(execution.get("provider_cost_usd", 0.0)),
        execution=dict(execution),
    )
