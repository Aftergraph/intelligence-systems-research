import time
from typing import Any, Callable, Dict, List, Optional
from providers.router import ModelRouter
from capabilities.dispatcher import CapabilityDispatcher
from telemetry.events import TrajectoryRecorder
from telemetry.cost_meter import CostMeter, BudgetExceededError
from state.journal import EventJournal
from agent.context_manager import ContextManager

# ponytail: Hardened Iterative Agent Execution Loop.
# Multi-turn bounded cycle: Context -> Model -> Capability -> Observation -> Journal -> Model.
# Tool execution DOES NOT terminate the run; observations feed back into next model turn.

class AgentExecutionLoop:
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

        # Control flags
        self.is_paused = False
        self.is_cancelled = False
        self.is_takeover = False

    def pause(self):
        self.is_paused = True
        self.trajectory.emit_event("HUMAN_CONTROL_PAUSE", {})

    def resume(self):
        self.is_paused = False
        self.trajectory.emit_event("HUMAN_CONTROL_RESUME", {})

    def cancel(self, reason: str = "Operator cancelled"):
        self.is_cancelled = True
        self.trajectory.emit_event("HUMAN_CONTROL_CANCEL", {"reason": reason})

    def run_step(
        self,
        mission_id: str,
        user_or_system_prompt: str,
        system_prompt: str,
        delegation_token: Dict[str, Any],
        preferred_provider: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Runs a single step for backward-compatibility."""
        return self.run_iterative_loop(
            mission_id=mission_id,
            system_prompt=system_prompt,
            initial_prompt=user_or_system_prompt,
            delegation_token=delegation_token,
            max_iterations=1,
            preferred_provider=preferred_provider,
            dry_run=dry_run
        )

    def run_iterative_loop(
        self,
        mission_id: str,
        system_prompt: str,
        initial_prompt: str,
        delegation_token: Dict[str, Any],
        max_iterations: int = 10,
        preferred_provider: Optional[str] = None,
        context_manager: Optional[ContextManager] = None,
        dry_run: bool = False,
        simulated_tool_responses: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Executes a bounded, failure-tolerant multi-turn reasoning and tool execution loop."""
        ctx = context_manager or ContextManager()
        ctx.set_pinned_context(system_prompt=system_prompt, constraints=[])
        ctx.add_turn(role="user", content=initial_prompt)

        iteration = 0
        last_resp = None
        executed_tools = []
        sim_step = 0

        while iteration < max_iterations:
            if self.is_cancelled:
                return {
                    "type": "EXECUTION_ABORTED",
                    "status": "CANCELLED",
                    "iterations": iteration,
                    "tool_results": executed_tools
                }

            if self.is_paused:
                return {
                    "type": "EXECUTION_SUSPENDED",
                    "status": "PAUSED",
                    "iterations": iteration,
                    "tool_results": executed_tools
                }

            if delegation_token.get("revoked", False):
                raise PermissionError("Authority revoked mid-execution")

            iteration += 1

            # 1. Atomic Two-Phase Budget Reservation
            res_id = self.cost_meter.reserve(
                mission_id=mission_id,
                estimated_tokens=500,
                estimated_cost_usd=0.01,
                estimated_tool_calls=1,
                estimated_model_calls=1
            )

            # 2. Model Resolution
            prov_name, model_id, routing_receipt = self.router.route_request(
                mission_id=mission_id,
                preferred_provider=preferred_provider
            )

            # 3. Model Invocation
            assembled = ctx.get_assembled_context()
            last_user_msg = assembled[-1]["content"] if assembled else initial_prompt

            try:
                resp = self.router.generate_with_fallback(
                    prompt=last_user_msg,
                    system_prompt=system_prompt,
                    model_id=model_id,
                    provider_name=prov_name,
                    dry_run=dry_run
                )

                # Commit budget
                self.cost_meter.commit(
                    reservation_id=res_id,
                    actual_tokens=resp.total_tokens,
                    actual_cost_usd=resp.cost_usd,
                    provider=resp.provider,
                    actual_tool_calls=len(resp.tool_calls),
                    actual_model_calls=1
                )
            except Exception as e:
                self.cost_meter.release(res_id)
                raise e

            last_resp = resp
            if self.journal:
                self.journal.append_event(
                    event_type="model.invoked",
                    payload={"provider": resp.provider, "model": resp.model_id, "tokens": resp.total_tokens}
                )

            # 4. Check for Simulated Tool Sequencing (for testing multi-step workflows)
            current_tool_calls = list(resp.tool_calls)
            if simulated_tool_responses and sim_step < len(simulated_tool_responses):
                st = simulated_tool_responses[sim_step]
                sim_step += 1
                current_tool_calls.append({
                    "function": {
                        "name": st.get("capability_uri", "tool://inspect"),
                        "arguments": st.get("payload", {})
                    }
                })

            # 5. Handle Capability Calls
            if current_tool_calls:
                for tc in current_tool_calls:
                    func = tc.get("function", {})
                    cap_uri = func.get("name", "")
                    args = func.get("arguments", {})

                    if self.journal:
                        self.journal.append_event(
                            event_type="capability.requested",
                            payload={"capability": cap_uri, "arguments": args}
                        )

                    # Execute via dispatcher
                    dispatch_res = self.dispatcher.dispatch(
                        capability_uri=cap_uri,
                        payload=args,
                        delegation_token=delegation_token
                    )
                    executed_tools.append(dispatch_res)

                    if self.journal:
                        self.journal.append_event(
                            event_type="capability.completed",
                            payload=dispatch_res
                        )

                    # Feed observation back into context manager
                    ctx.add_observation(cap_uri, dispatch_res.get("result"))

                # Continue iteration to allow model to inspect observation!
                continue

            # If no more tools called, we have a candidate completion
            break

        candidate_completion = {
            "type": "CANDIDATE_COMPLETION",
            "content": last_resp.content if last_resp else "No response",
            "tool_results": executed_tools,
            "model": last_resp.model_id if last_resp else "unknown",
            "provider": last_resp.provider if last_resp else "unknown",
            "iterations": iteration
        }

        if self.journal:
            self.journal.append_event(
                event_type="candidate_completion.created",
                payload={"model": candidate_completion["model"], "iterations": iteration}
            )

        self.trajectory.emit_event("CANDIDATE_COMPLETION_EMITTED", {
            "mission_id": mission_id,
            "iterations": iteration,
            "tool_count": len(executed_tools)
        })

        return candidate_completion
