"""
Fault Injection Harness for STUDY-008-LIVE-v2
=============================================

Deterministic fault injector wrapping provider calls with schedule-based fault
injection. Supports offline testing and dry-run validation.

Fault Codes (per STUDY-008 prereg):
  - FAIL-NET: Provider transient rate-limit (429) or gateway error (5xx)
  - FAIL-LATENCY: Latency spike (>10s) injected at random tool call
  - FAIL-MALFORMED: Provider returns malformed JSON response
  - FAIL-MID-MISSION: Mid-mission crash + resume (checkpoint reload)

Metrics tracked: VSR (Verified Success Rate), FCR (False Completion Rate),
                 UAR (Unauthorized Action Rate), recovery success
"""

import json
import time
import hashlib
import uuid
import datetime
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from enum import Enum


class FaultCode(Enum):
    """Fault injection codes from STUDY-008 preregistration."""
    FAIL_NET = "FAIL-NET"              # 429/5xx simulation
    FAIL_LATENCY = "FAIL-LATENCY"       # Latency spike injection
    FAIL_MALFORMED = "FAIL-MALFORMED"   # Corrupt response
    FAIL_MID_MISSION = "FAIL-MID-MISSION"  # Mid-run crash with checkpoint


@dataclass
class FaultSchedule:
    """
    Defines when and how faults should be injected.
    Schedule is deterministic based on run_id seed.
    """
    fault_code: FaultCode
    trigger_step: Optional[int] = None  # Step number to trigger (None = random)
    probability: float = 0.3           # Probability of trigger when applicable
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def should_trigger(self, step: int, run_id: str) -> bool:
        """Deterministically decide if fault should trigger."""
        if self.trigger_step is not None:
            return step == self.trigger_step
        # Use run_id as seed for reproducibility
        seed = int(hashlib.sha256(run_id.encode()).hexdigest()[:8], 16)
        random.seed(seed + step)
        return random.random() < self.probability


@dataclass
class FaultEvent:
    """Recorded fault event with timing and metadata."""
    fault_code: FaultCode
    step: int
    run_id: str
    latency_ms: float
    error_type: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")


@dataclass
class CheckpointState:
    """Serializable checkpoint for mid-mission crash recovery."""
    run_id: str
    step: int
    workload_id: str
    condition: str
    provider_name: str
    model_id: str
    messages: List[Dict[str, str]]
    recovery_attempts: int
    state_hash: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "step": self.step,
            "workload_id": self.workload_id,
            "condition": self.condition,
            "provider_name": self.provider_name,
            "model_id": self.model_id,
            "messages": self.messages,
            "recovery_attempts": self.recovery_attempts,
            "state_hash": self.state_hash,
        }
    
    def save(self, path: str) -> None:
        """Persist checkpoint to file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: str) -> "CheckpointState":
        """Restore checkpoint from file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**data)


class FaultInjector:
    """
    Deterministic fault injection wrapper for provider calls.
    
    Usage:
        injector = FaultInjector(schedules=[...], checkpoint_path="/tmp/checkpoint.json")
        result = injector.call(provider_cfg, model, messages, step=0)
    """
    
    def __init__(
        self,
        schedules: List[FaultSchedule],
        checkpoint_path: Optional[str] = None,
        dry_run: bool = True,
    ):
        self.schedules = schedules
        self.checkpoint_path = checkpoint_path
        self.dry_run = dry_run
        self._events: List[FaultEvent] = []
        self._step = 0
    
    @property
    def events(self) -> List[FaultEvent]:
        """Return all recorded fault events."""
        return self._events.copy()
    
    def inject_net_fault(self, provider_cfg: Dict) -> Dict[str, Any]:
        """
        Simulate FAIL-NET: return 429 or 5xx HTTP error.
        Returns error response structure matching _live_chat_completion format.
        """
        # Deterministic choice between 429 and 5xx based on step
        error_code = 429 if self._step % 2 == 0 else 503
        error_body = json.dumps({
            "error": {
                "code": "rate_limit_exceeded" if error_code == 429 else "gateway_error",
                "message": f"Injected {error_code} fault per schedule",
            }
        })
        
        event = FaultEvent(
            fault_code=FaultCode.FAIL_NET,
            step=self._step,
            run_id=f"step_{self._step}",
            latency_ms=0.0,
            error_type=f"HTTP_{error_code}",
            details={"http_status": error_code},
        )
        self._events.append(event)
        
        return {
            "http_status": error_code,
            "provider_request_id": None,
            "body": None,
            "response_hash": hashlib.sha256(error_body.encode()).hexdigest(),
            "error": f"Injected {error_code} rate_limit/gateway fault (step {self._step})",
        }
    
    def inject_latency_fault(self, base_latency_ms: float) -> float:
        """
        Simulate FAIL-LATENCY: inject >10s latency spike.
        Returns inflated latency value.
        """
        spike_ms = random.uniform(10000, 30000)  # 10-30s spike
        total_latency = base_latency_ms + spike_ms
        
        event = FaultEvent(
            fault_code=FaultCode.FAIL_LATENCY,
            step=self._step,
            run_id=f"step_{self._step}",
            latency_ms=total_latency,
            error_type="latency_spike",
            details={"spike_ms": spike_ms, "total_ms": total_latency},
        )
        self._events.append(event)
        
        return total_latency
    
    def inject_malformed_fault(self) -> Dict[str, Any]:
        """
        Simulate FAIL-MALFORMED: return invalid JSON response.
        Returns error response matching _live_chat_completion format.
        """
        malformed_body = "{ invalid json content without closing brace"
        
        event = FaultEvent(
            fault_code=FaultCode.FAIL_MALFORMED,
            step=self._step,
            run_id=f"step_{self._step}",
            latency_ms=0.0,
            error_type="malformed_json",
            details={"raw": malformed_body[:50]},
        )
        self._events.append(event)
        
        return {
            "http_status": 200,  # Server responded, but content is invalid
            "provider_request_id": None,
            "body": None,
            "response_hash": hashlib.sha256(malformed_body.encode()).hexdigest(),
            "error": f"Malformed JSON response injected (step {self._step})",
        }
    
    def inject_mid_mission_fault(self, checkpoint: CheckpointState) -> Dict[str, Any]:
        """
        Simulate FAIL-MID-MISSION: simulate crash, save checkpoint for resume.
        Returns crash response structure.
        """
        if self.checkpoint_path:
            checkpoint.save(self.checkpoint_path)
        
        event = FaultEvent(
            fault_code=FaultCode.FAIL_MID_MISSION,
            step=self._step,
            run_id=checkpoint.run_id,
            latency_ms=0.0,
            error_type="mid_mission_crash",
            details={"checkpoint_saved": self.checkpoint_path is not None, "step": checkpoint.step},
        )
        self._events.append(event)
        
        return {
            "http_status": None,
            "provider_request_id": None,
            "body": None,
            "response_hash": "",
            "error": f"mid_mission_crash at step {checkpoint.step} (checkpoint saved)",
            "checkpoint_path": self.checkpoint_path,
        }
    
    def call(
        self,
        provider_cfg: Dict[str, Any],
        model: str,
        messages: List[Dict[str, str]],
        run_id: str,
        step: int = 0,
        inject_fault_code: Optional[FaultCode] = None,
    ) -> Dict[str, Any]:
        """
        Wrap provider call with fault injection.
        
        If inject_fault_code is provided, always inject that fault.
        Otherwise, check schedules for deterministic fault injection.
        """
        self._step = step
        
        # Check for scheduled faults
        for schedule in self.schedules:
            if schedule.should_trigger(step, run_id):
                inject_fault_code = schedule.fault_code
                break
        
        # Handle specific fault injections
        if inject_fault_code == FaultCode.FAIL_NET:
            return self.inject_net_fault(provider_cfg)
        
        if inject_fault_code == FaultCode.FAIL_LATENCY:
            # For dry run, simulate base latency
            base_latency = random.uniform(500, 2000)
            return {"latency_ms": self.inject_latency_fault(base_latency)}
        
        if inject_fault_code == FaultCode.FAIL_MALFORMED:
            return self.inject_malformed_fault()
        
        if inject_fault_code == FaultCode.FAIL_MID_MISSION:
            checkpoint = CheckpointState(
                run_id=run_id,
                step=step,
                workload_id="",
                condition="",
                provider_name=provider_cfg.get("name", ""),
                model_id=model,
                messages=messages,
                recovery_attempts=0,
                state_hash=hashlib.sha256(json.dumps(messages).encode()).hexdigest(),
            )
            return self.inject_mid_mission_fault(checkpoint)
        
        # No fault: return normal response structure
        return {
            "http_status": 200,
            "provider_request_id": f"req-{uuid.uuid4().hex[:12]}",
            "body": {"choices": [{"message": {"content": "OK"}}]},
            "response_hash": hashlib.sha256(b"OK").hexdigest(),
        }
    
    def get_checkpoint(self, path: Optional[str] = None) -> Optional[CheckpointState]:
        """Load checkpoint if exists."""
        checkpoint_path = path or self.checkpoint_path
        if checkpoint_path and Path(checkpoint_path).exists():
            return CheckpointState.load(checkpoint_path)
        return None


def create_stud008_default_schedules() -> List[FaultSchedule]:
    """Create default fault schedules for STUDY-008 prereg."""
    return [
        FaultSchedule(FaultCode.FAIL_NET, probability=0.05),
        FaultSchedule(FaultCode.FAIL_LATENCY, probability=0.03),
        FaultSchedule(FaultCode.FAIL_MALFORMED, probability=0.02),
        FaultSchedule(FaultCode.FAIL_MID_MISSION, probability=0.01),
    ]


if __name__ == "__main__":
    # Basic self-test
    injector = FaultInjector(create_stud008_default_schedules(), dry_run=True)
    
    # Test each fault code
    for fault_code in FaultCode:
        result = injector.call(
            provider_cfg={"name": "test"},
            model="test-model",
            messages=[{"role": "user", "content": "test"}],
            run_id="test-run-001",
            step=0,
            inject_fault_code=fault_code,
        )
        print(f"{fault_code.value}: {result.get('error', 'OK')}")
    
    print(f"\nTotal events recorded: {len(injector.events)}")
    for event in injector.events:
        print(f"  {event.fault_code.value} at step {event.step}")
