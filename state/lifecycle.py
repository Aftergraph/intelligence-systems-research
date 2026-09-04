# ponytail: Discrete Finite State Machine for SPEC-001 Mission Lifecycle.
# Enforces Invariant 1 (Complete != Verified) and Invariant 2 (Evidence Gated).

VALID_LIFECYCLE_STATES = {
    "DRAFT", "READY", "AUTHORIZED", "RUNNING", "PAUSED",
    "VERIFYING", "VERIFIED", "RECOVERING", "NEEDS_INPUT",
    "FAILED", "CANCELLED", "REVOKED"
}

ALLOWED_TRANSITIONS = {
    "DRAFT": {"READY", "CANCELLED"},
    "READY": {"AUTHORIZED", "CANCELLED"},
    "AUTHORIZED": {"RUNNING", "CANCELLED", "REVOKED"},
    "RUNNING": {"PAUSED", "VERIFYING", "NEEDS_INPUT", "CANCELLED", "REVOKED"},
    "PAUSED": {"RUNNING", "CANCELLED", "REVOKED"},
    "VERIFYING": {"VERIFIED", "RECOVERING", "NEEDS_INPUT", "FAILED"},
    "RECOVERING": {"RUNNING", "NEEDS_INPUT", "FAILED"},
    "NEEDS_INPUT": {"RUNNING", "PAUSED", "CANCELLED", "FAILED"},
    "VERIFIED": set(),
    "FAILED": set(),
    "CANCELLED": set(),
    "REVOKED": set()
}

class MissionLifecycle:
    def __init__(self, initial_state: str = "DRAFT"):
        assert initial_state in VALID_LIFECYCLE_STATES
        self._current_state = initial_state

    @property
    def current_state(self) -> str:
        return self._current_state

    def transition_to(self, new_state: str, reason: str = "") -> str:
        if new_state not in VALID_LIFECYCLE_STATES:
            raise ValueError(f"Invalid lifecycle state: {new_state}")

        allowed = ALLOWED_TRANSITIONS.get(self._current_state, set())
        if new_state not in allowed:
            raise RuntimeError(
                f"Illegal lifecycle transition: '{self._current_state}' -> '{new_state}'. "
                f"Allowed transitions: {list(allowed)}. (Reason: {reason})"
            )

        self._current_state = new_state
        return self._current_state
