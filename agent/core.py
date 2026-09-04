from typing import Any, Dict, List, Optional
from agent.prompt_compiler import PromptCompiler
from agent.context_manager import ContextManager
from agent.execution_loop import AgentExecutionLoop
from providers.router import ModelRouter
from capabilities.dispatcher import CapabilityDispatcher
from telemetry.events import TrajectoryRecorder
from telemetry.cost_meter import CostMeter
from state.journal import EventJournal

# ponytail: In-House Intelligence Agent Coordinator.
# Invariant: InHouseAgent can produce ONLY a candidate completion; it CANNOT mutate lifecycle to VERIFIED!

class InHouseAgent:
    def __init__(
        self,
        router: ModelRouter,
        dispatcher: CapabilityDispatcher,
        trajectory: TrajectoryRecorder,
        cost_meter: CostMeter,
        journal: Optional[EventJournal] = None
    ):
        self.router = router
        self.dispatcher = dispatcher
        self.trajectory = trajectory
        self.cost_meter = cost_meter
        self.journal = journal
        self.prompt_compiler = PromptCompiler()
        self.context_manager = ContextManager()
        self.execution_loop = AgentExecutionLoop(
            router=self.router,
            dispatcher=self.dispatcher,
            trajectory=self.trajectory,
            cost_meter=self.cost_meter,
            journal=self.journal
        )

    # Human Interaction Loop Controls
    def pause(self):
        self.execution_loop.pause()

    def resume(self):
        self.execution_loop.resume()

    def cancel(self, reason: str = "Operator aborted mission"):
        self.execution_loop.cancel(reason=reason)

    def takeover(self, operator_action: Dict[str, Any]) -> Dict[str, Any]:
        """Operator directly executes an action through the dispatcher."""
        self.trajectory.emit_event("HUMAN_OPERATOR_TAKEOVER", operator_action)
        cap = operator_action.get("capability_uri")
        payload = operator_action.get("payload")
        token = operator_action.get("delegation_token")
        return self.dispatcher.dispatch(capability_uri=cap, payload=payload, delegation_token=token)

    def execute_turn(
        self,
        mission_id: str,
        objective: str,
        constraints: List[str],
        criteria_ids: List[str],
        allowed_capabilities: List[str],
        delegation_token: Dict[str, Any],
        budget_remaining: Optional[Dict[str, Any]] = None,
        diagnostic_feedback: Optional[str] = None,
        preferred_provider: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Runs a single agent turn (for backward-compatibility)."""
        tier1_prompt = self.prompt_compiler.compile_tier1_prompt(
            mission_id=mission_id,
            objective=objective,
            constraints=constraints,
            criteria_ids=criteria_ids,
            allowed_capabilities=allowed_capabilities,
            budget_remaining=budget_remaining or {"tokens": 10000, "usd": 0.50},
            diagnostic_feedback=diagnostic_feedback
        )

        self.context_manager.set_pinned_control_context(
            mission_id=mission_id,
            objective=objective,
            constraints=constraints,
            criteria_ids=criteria_ids,
            remaining_budget=budget_remaining or {"tokens": 10000, "usd": 0.50}
        )

        return self.execution_loop.run_step(
            mission_id=mission_id,
            user_or_system_prompt="Proceed with mission execution.",
            system_prompt=tier1_prompt,
            delegation_token=delegation_token,
            preferred_provider=preferred_provider,
            dry_run=dry_run
        )

    def execute_mission_loop(
        self,
        mission_id: str,
        objective: str,
        constraints: List[str],
        criteria_ids: List[str],
        allowed_capabilities: List[str],
        delegation_token: Dict[str, Any],
        budget_remaining: Optional[Dict[str, Any]] = None,
        max_iterations: int = 10,
        preferred_provider: Optional[str] = None,
        dry_run: bool = False,
        simulated_tool_responses: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Runs a full iterative reasoning and tool execution loop."""
        tier1_prompt = self.prompt_compiler.compile_tier1_prompt(
            mission_id=mission_id,
            objective=objective,
            constraints=constraints,
            criteria_ids=criteria_ids,
            allowed_capabilities=allowed_capabilities,
            budget_remaining=budget_remaining or {"tokens": 10000, "usd": 0.50}
        )

        self.context_manager.set_pinned_control_context(
            mission_id=mission_id,
            objective=objective,
            constraints=constraints,
            criteria_ids=criteria_ids,
            remaining_budget=budget_remaining or {"tokens": 10000, "usd": 0.50}
        )

        return self.execution_loop.run_iterative_loop(
            mission_id=mission_id,
            system_prompt=tier1_prompt,
            initial_prompt="Proceed with mission execution.",
            delegation_token=delegation_token,
            max_iterations=max_iterations,
            preferred_provider=preferred_provider,
            context_manager=self.context_manager,
            dry_run=dry_run,
            simulated_tool_responses=simulated_tool_responses
        )
