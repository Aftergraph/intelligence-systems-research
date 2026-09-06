from __future__ import annotations


class BrowserUnavailable(RuntimeError):
    """Raised when a browser runtime is not installed or cannot start."""


class BrowserUnsupported(RuntimeError):
    """Raised when a browser feature is explicitly unsupported."""


class DelegatingBrowserAdapter:
    """Small adapter around a host backend exposing perform(operation, payload)."""

    def __init__(self, backend):
        if backend is None:
            raise BrowserUnavailable("browser backend is unavailable")
        self._backend = backend

    def perform(self, operation: str, payload: dict | None = None):
        return self._backend.perform(operation, payload or {})

    def start(self):
        return self.perform("start", {})

    def navigate(self, url: str):
        return self.perform("navigate", {"url": url})

    def evaluate(self, script: str):
        return self.perform("evaluate", {"script": script})

    def query(self, selector: str):
        return self.perform("query", {"selector": selector})

    def screenshot(self, path: str):
        return self.perform("screenshot", {"path": path})

    def close(self):
        return self.perform("close", {})
