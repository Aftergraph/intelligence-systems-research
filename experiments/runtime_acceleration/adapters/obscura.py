from __future__ import annotations

from .browser_base import DelegatingBrowserAdapter

OBSCURA_PIN = "a1e09de68c7617b8079fbb1661b0548c501971c1"


class ObscuraAdapter(DelegatingBrowserAdapter):
    """Obscura treatment adapter pinned to the preregistered revision."""

    def __init__(self, backend, *, actual_revision: str):
        if actual_revision != OBSCURA_PIN:
            raise ValueError(f"Obscura revision mismatch: expected {OBSCURA_PIN}, got {actual_revision}")
        super().__init__(backend)
        self.actual_revision = actual_revision
