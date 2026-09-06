import pytest

from experiments.runtime_acceleration.adapters.base import TreatmentSetupError
from experiments.runtime_acceleration.adapters.stock_hermes import StockHermesAdapter
from experiments.runtime_acceleration.adapters.toolrush import TOOLRUSH_PIN, ToolRushAdapter


def test_stock_adapter_dispatches_named_operation():
    adapter = StockHermesAdapter({"read": lambda payload: {"text": payload["path"]}})
    assert adapter.execute("read", {"path": "a.py"}) == {"text": "a.py"}


def test_toolrush_requires_explicit_enablement():
    with pytest.raises(TreatmentSetupError):
        ToolRushAdapter({}, enabled=False, actual_revision=TOOLRUSH_PIN)


def test_toolrush_requires_exact_frozen_revision():
    with pytest.raises(TreatmentSetupError):
        ToolRushAdapter({}, enabled=True, actual_revision="0" * 40)


def test_toolrush_accepts_exact_revision_and_dispatches():
    adapter = ToolRushAdapter({"search": lambda payload: {"matches": [payload["query"]]}}, enabled=True, actual_revision=TOOLRUSH_PIN)
    assert adapter.execute("search", {"query": "needle"}) == {"matches": ["needle"]}
