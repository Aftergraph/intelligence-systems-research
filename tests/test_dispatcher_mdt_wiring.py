"""
test_dispatcher_mdt_wiring.py
=============================

ADR-008 Phase 8: pins the wiring of the MDT (Mission Delegation
Token) verification into CapabilityDispatcher.dispatch.

Contract:
- A signed JWT delegation token (str) + mdt_secret set => verified
  fail-closed before authority evaluation; decoded claims replace
  the token for downstream evaluation.
- A forged/expired/out-of-scope JWT is rejected with TokenExchangeError.
- Legacy dict delegation tokens bypass MDT verification (backward compat).
- No mdt_secret configured + str token => not MDT-verified (legacy behavior
  preserved; the str is passed through).
"""

import os
import sys
import time

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from capabilities.dispatcher import CapabilityDispatcher, CapabilityResolver
from capabilities.registry import Capability, CapabilityRegistry
from delegation.token_exchange import (
    TokenExchangeError,
    exchange_token,
    issue_mission_token,
)

SECRET = "dispatcher-wiring-test-secret"
URI = "mcp://github/repo:read"
SCOPE = ["mcp://github/repo:read", "mcp://github/repo:write"]
CONSTRAINTS = {"required": ["tests pass"]}
OBJECTIVE = "Do the thing safely."


def _make_dispatcher(mdt_secret=SECRET):
    registry = CapabilityRegistry()
    registry.register(Capability(
        uri=URI, description="read repo",
        handler=lambda payload: {"status": "SUCCESS", "read": True},
    ))
    return CapabilityDispatcher(
        resolver=CapabilityResolver(registry),
        mdt_secret=mdt_secret,
    )


SECRET = "dispatcher-wiring-test-secret"


@pytest.fixture
def mdt_token():
    return issue_mission_token(
        mission_id="msn-wiring", mission_version=1,
        objective_text=OBJECTIVE, constraints=CONSTRAINTS,
        scope_allowed=SCOPE, secret=SECRET,
    )


def test_signed_mdt_passes_and_dispatches(mdt_token):
    d = _make_dispatcher()
    receipt = d.dispatch(URI, payload={"x": 1}, delegation_token=mdt_token)
    assert receipt["status"] == "COMPLETED"


def test_forged_mdt_rejected():
    import jwt as pyjwt
    d = _make_dispatcher()
    forged = jwt_module_encode_with_wrong_secret()
    with pytest.raises(TokenExchangeError):
        d.dispatch(URI, delegation_token=forged)


def jwt_module_encode_with_wrong_secret():
    import jwt as pyjwt
    return pyjwt.encode(
        {"purpose": "urn:mission:msn-wiring:v1",
         "scope": {"allowed": SCOPE, "denied": []},
         "depth": 0, "iss": "attacker", "sub": "attacker",
         "iat": int(time.time()), "exp": int(time.time()) + 600},
        "wrong-secret", algorithm="HS256",
    )


def test_out_of_scope_mdt_rejected():
    """Token valid but capability not in allowed scope -> fail-closed."""
    token = issue_mission_token(
        mission_id="msn-wiring", mission_version=1,
        objective_text=OBJECTIVE, constraints=CONSTRAINTS,
        scope_allowed=["mcp://other/cap:read"], secret=SECRET,
    )
    d = _make_dispatcher()
    with pytest.raises(TokenExchangeError) as exc:
        d.dispatch(URI, delegation_token=token)
    assert "not in allowed scope" in str(exc.value)


def test_attenuated_child_token_can_dispatch_subset():
    root = issue_mission_token(
        mission_id="msn-wiring", mission_version=1,
        objective_text=OBJECTIVE, constraints=CONSTRAINTS,
        scope_allowed=SCOPE, secret=SECRET,
    )
    child = exchange_token(root, ["mcp://github/repo:read"], secret=SECRET)
    d = _make_dispatcher()
    receipt = d.dispatch(URI, delegation_token=child)
    assert receipt["status"] == "COMPLETED"


def test_legacy_dict_token_still_works():
    """Backward compat: dict tokens take the legacy path (no MDT verify)."""
    d = _make_dispatcher()
    receipt = d.dispatch(
        URI, delegation_token={"scope": {"allowed": [URI]}},
    )
    assert receipt["status"] == "COMPLETED"


def test_no_mdt_secret_str_token_passthrough():
    """Without mdt_secret, a str token is not MDT-verified (legacy behavior)."""
    d = _make_dispatcher(mdt_secret=None)
    receipt = d.dispatch(URI, delegation_token="any-string-token")
    assert receipt["status"] == "COMPLETED"


def test_mdt_rejection_happens_before_execution():
    """Fail-closed: the capability handler must NOT run when the MDT
    fails verification. We detect execution via a flag."""
    executed = {"flag": False}

    def handler(payload):
        executed["flag"] = True
        return {"status": "SUCCESS"}

    registry = CapabilityRegistry()
    registry.register(Capability(
        uri=URI, description="x", handler=handler,
    ))
    d = CapabilityDispatcher(resolver=CapabilityResolver(registry), mdt_secret=SECRET)
    forged = jwt_module_encode_with_wrong_secret()
    with pytest.raises(TokenExchangeError):
        d.dispatch(URI, delegation_token=forged)
    assert executed["flag"] is False, (
        "Capability handler executed despite failed MDT verification. "
        "Fail-closed violated."
    )


from delegation.token_exchange import TokenExchangeError  # noqa: E402
