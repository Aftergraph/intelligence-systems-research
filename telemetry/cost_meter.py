from collections import defaultdict
import threading
import uuid
from typing import Any, Dict, Optional

# ponytail: Atomic Global Mission Budget Governance.
# Implements 2-Phase Reservation Pattern: RESERVE -> VALIDATE -> EXECUTE -> COMMIT / RELEASE.
# Thread-safe reentrant lock guarantees safety across concurrent subagents.

class BudgetExceededError(RuntimeError):
    pass

class CostMeter:
    def __init__(
        self,
        max_tokens: Optional[int] = None,
        max_cost_usd: Optional[float] = None,
        max_tool_calls: Optional[int] = None,
        max_model_calls: Optional[int] = None
    ):
        self._lock = threading.RLock()
        self.max_tokens = max_tokens
        self.max_cost_usd = max_cost_usd
        self.max_tool_calls = max_tool_calls
        self.max_model_calls = max_model_calls

        # Committed usage
        self.total_tokens_by_mission = defaultdict(int)
        self.total_cost_by_mission = defaultdict(float)
        self.tool_calls_by_mission = defaultdict(int)
        self.model_calls_by_mission = defaultdict(int)

        self.tokens_by_provider = defaultdict(int)
        self.cost_by_provider = defaultdict(float)

        # Active reservations: reservation_id -> dict
        self._active_reservations: Dict[str, Dict[str, Any]] = {}
        self._reserved_tokens_by_mission = defaultdict(int)
        self._reserved_cost_by_mission = defaultdict(float)
        self._reserved_tool_calls_by_mission = defaultdict(int)
        self._reserved_model_calls_by_mission = defaultdict(int)

    def reserve(
        self,
        mission_id: str,
        estimated_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
        estimated_tool_calls: int = 0,
        estimated_model_calls: int = 1
    ) -> str:
        """Atomically reserves budget before execution. Raises BudgetExceededError if limit violated."""
        with self._lock:
            # Check projected tokens
            curr_tok = self.total_tokens_by_mission[mission_id] + self._reserved_tokens_by_mission[mission_id]
            if self.max_tokens is not None and (curr_tok + estimated_tokens) > self.max_tokens:
                raise BudgetExceededError(
                    f"Mission {mission_id} exceeded token ceiling: "
                    f"cannot reserve {estimated_tokens} tokens (projected {curr_tok + estimated_tokens} > {self.max_tokens})"
                )

            # Check projected USD
            curr_usd = self.total_cost_by_mission[mission_id] + self._reserved_cost_by_mission[mission_id]
            if self.max_cost_usd is not None and (curr_usd + estimated_cost_usd) > self.max_cost_usd:
                raise BudgetExceededError(
                    f"Mission {mission_id} exceeded USD cost ceiling: "
                    f"cannot reserve ${estimated_cost_usd:.4f} (projected ${curr_usd + estimated_cost_usd:.4f} > ${self.max_cost_usd:.4f})"
                )

            # Check tool calls
            curr_tools = self.tool_calls_by_mission[mission_id] + self._reserved_tool_calls_by_mission[mission_id]
            if self.max_tool_calls is not None and (curr_tools + estimated_tool_calls) > self.max_tool_calls:
                raise BudgetExceededError(
                    f"Mission {mission_id} tool calls limit reached: "
                    f"{curr_tools + estimated_tool_calls} > {self.max_tool_calls}"
                )

            res_id = f"res-{uuid.uuid4().hex[:12]}"
            res_entry = {
                "reservation_id": res_id,
                "mission_id": mission_id,
                "tokens": estimated_tokens,
                "cost_usd": estimated_cost_usd,
                "tool_calls": estimated_tool_calls,
                "model_calls": estimated_model_calls
            }
            self._active_reservations[res_id] = res_entry
            self._reserved_tokens_by_mission[mission_id] += estimated_tokens
            self._reserved_cost_by_mission[mission_id] += estimated_cost_usd
            self._reserved_tool_calls_by_mission[mission_id] += estimated_tool_calls
            self._reserved_model_calls_by_mission[mission_id] += estimated_model_calls
            return res_id

    def commit(
        self,
        reservation_id: str,
        actual_tokens: int,
        actual_cost_usd: float,
        provider: str = "default",
        actual_tool_calls: int = 0,
        actual_model_calls: int = 1
    ):
        """Commits actual executed usage and clears reservation."""
        with self._lock:
            res = self._active_reservations.pop(reservation_id, None)
            if res:
                m_id = res["mission_id"]
                self._reserved_tokens_by_mission[m_id] -= res["tokens"]
                self._reserved_cost_by_mission[m_id] -= res["cost_usd"]
                self._reserved_tool_calls_by_mission[m_id] -= res["tool_calls"]
                self._reserved_model_calls_by_mission[m_id] -= res["model_calls"]
            else:
                m_id = "unknown"

            self.total_tokens_by_mission[m_id] += actual_tokens
            self.total_cost_by_mission[m_id] += actual_cost_usd
            self.tool_calls_by_mission[m_id] += actual_tool_calls
            self.model_calls_by_mission[m_id] += actual_model_calls

            self.tokens_by_provider[provider] += actual_tokens
            self.cost_by_provider[provider] += actual_cost_usd

    def release(self, reservation_id: str):
        """Releases reservation on failure or cancellation without committing usage."""
        with self._lock:
            res = self._active_reservations.pop(reservation_id, None)
            if res:
                m_id = res["mission_id"]
                self._reserved_tokens_by_mission[m_id] -= res["tokens"]
                self._reserved_cost_by_mission[m_id] -= res["cost_usd"]
                self._reserved_tool_calls_by_mission[m_id] -= res["tool_calls"]
                self._reserved_model_calls_by_mission[m_id] -= res["model_calls"]

    def record_usage(
        self,
        mission_id: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        tool_calls: int = 0,
        model_calls: int = 1
    ):
        """One-step atomic reserve-and-commit for direct callers."""
        total_tok = prompt_tokens + completion_tokens
        with self._lock:
            r_id = self.reserve(
                mission_id=mission_id,
                estimated_tokens=total_tok,
                estimated_cost_usd=cost_usd,
                estimated_tool_calls=tool_calls,
                estimated_model_calls=model_calls
            )
            self.commit(
                reservation_id=r_id,
                actual_tokens=total_tok,
                actual_cost_usd=cost_usd,
                provider=provider,
                actual_tool_calls=tool_calls,
                actual_model_calls=model_calls
            )

    def get_mission_summary(self, mission_id: str) -> Dict[str, Any]:
        with self._lock:
            return {
                "mission_id": mission_id,
                "tokens": self.total_tokens_by_mission[mission_id],
                "cost_usd": self.total_cost_by_mission[mission_id],
                "tool_calls": self.tool_calls_by_mission[mission_id],
                "model_calls": self.model_calls_by_mission[mission_id],
                "reserved_tokens": self._reserved_tokens_by_mission[mission_id],
                "reserved_usd": self._reserved_cost_by_mission[mission_id]
            }

    def get_provider_summary(self, provider: str) -> Dict[str, Any]:
        with self._lock:
            return {
                "provider": provider,
                "tokens": self.tokens_by_provider[provider],
                "cost_usd": self.cost_by_provider[provider]
            }
