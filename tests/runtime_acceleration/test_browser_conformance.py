import pytest

from experiments.runtime_acceleration.adapters.browser_base import BrowserUnsupported
from experiments.runtime_acceleration.adapters.obscura import OBSCURA_PIN, ObscuraAdapter
from experiments.runtime_acceleration.verification.browser_conformance import run_browser_conformance


class FakeBrowser:
    def __init__(self, values, unsupported=()):
        self.values = values
        self.unsupported = set(unsupported)

    def perform(self, operation, payload):
        if operation in self.unsupported:
            raise BrowserUnsupported(operation)
        return self.values[(operation, payload.get("id"))]


def test_browser_conformance_compares_semantic_observables():
    cases = [
        {"id": "nav", "operation": "navigate", "payload": {"id": "nav"}},
        {"id": "dom", "operation": "query", "payload": {"id": "dom"}},
    ]
    control = FakeBrowser({("navigate", "nav"): {"url": "/static"}, ("query", "dom"): {"text": "alpha"}})
    treatment = FakeBrowser({("navigate", "nav"): {"url": "/static"}, ("query", "dom"): {"text": "beta"}})
    result = run_browser_conformance(control, treatment, cases)
    assert result["passed"] == 1
    assert result["total"] == 2
    assert result["cases"][1]["classification"] == "SEMANTIC_MISMATCH"


def test_browser_conformance_records_explicit_unsupported():
    cases = [{"id": "pdf", "operation": "pdf", "payload": {"id": "pdf"}}]
    control = FakeBrowser({("pdf", "pdf"): {"bytes": 10}})
    treatment = FakeBrowser({}, unsupported={"pdf"})
    result = run_browser_conformance(control, treatment, cases)
    assert result["passed"] == 0
    assert result["cases"][0]["classification"] == "UNSUPPORTED"


def test_obscura_adapter_requires_frozen_revision():
    with pytest.raises(ValueError):
        ObscuraAdapter(FakeBrowser({}), actual_revision="0" * 40)
    adapter = ObscuraAdapter(FakeBrowser({}), actual_revision=OBSCURA_PIN)
    assert adapter.actual_revision == OBSCURA_PIN
