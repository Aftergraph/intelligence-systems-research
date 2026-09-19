from pathlib import Path

import pytest

from experiments.system_one_acceleration.calibration_preflight import (
    evaluate_calibration_preflight,
)
from experiments.system_one_acceleration.guarded_calibration import (
    CalibrationAuthorizationError,
    run_authorized_calibration,
)


ROOT = Path(__file__).resolve().parents[1]


class ExplodingClient:
    def system_one(self, **_kwargs):
        raise AssertionError("network-capable client must not be invoked while calibration is NO_GO")


def test_current_calibration_preflight_is_fail_closed():
    result = evaluate_calibration_preflight(ROOT)
    assert result.decision == "NO_GO"
    assert {
        "calibration_provider_call_ceiling_insufficient",
        "calibration_cost_ceiling_not_frozen",
        "calibration_approval_not_recorded",
        "calibration_network_calls_not_authorized",
        "calibration_cost_hard_stop_unavailable",
    }.issubset(set(result.blockers))


def test_cost_hard_stop_blocker_is_unconditional():
    result = evaluate_calibration_preflight(ROOT)
    assert "calibration_cost_hard_stop_unavailable" in result.blockers
    assert result.decision != "READY_TO_CALIBRATE"


def test_guarded_calibration_never_reaches_client_while_no_go():
    with pytest.raises(CalibrationAuthorizationError, match="calibration not authorized"):
        run_authorized_calibration(
            root=ROOT,
            client=ExplodingClient(),
            sdk=object(),
            contracts={},
        )
