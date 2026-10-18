from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any
from urllib.parse import urlparse
import uuid

import httpx

from .proof_graph import ProofGraph


class HttpEffectState(str, Enum):
    NEW = "new"
    PREPARED = "prepared"
    AUTHORIZED = "authorized"
    EXECUTED = "executed"
    READ_BACK = "read_back"
    VERIFIED = "verified"
    COMMITTED = "committed"
    COMPENSATED = "compensated"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class HttpActionProposal:
    action_id: str
    method: str
    url: str
    readback_url: str
    expected_status: int
    request_sha256: str
    expected_readback_sha256: str | None
    reversible: bool


@dataclass(frozen=True, slots=True)
class HttpEffectReceipt:
    action_id: str
    method: str
    url: str
    state: str
    principal: str
    authority_ref: str
    response_status: int
    response_sha256: str
    readback_sha256: str
    verifier_claim_ids: tuple[str, ...]


class HttpJsonEffectTransaction:
    """Proof-gated JSON HTTP effect with host allowlisting and exact readback binding.

    v1.6 deliberately requires an explicit host allowlist and a GET readback. It
    does not claim arbitrary HTTP mutations are reversible. Compensation is only
    available when the caller supplies a separate, explicit compensation request.
    """

    _METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, *, client: httpx.Client, allowed_hosts: set[str]) -> None:
        self.client = client
        self.allowed_hosts = {host.casefold() for host in allowed_hosts if host}
        if not self.allowed_hosts:
            raise ValueError("allowed_hosts must not be empty")
        self.state = HttpEffectState.NEW
        self.proposal: HttpActionProposal | None = None
        self.principal = ""
        self.authority_ref = ""
        self._payload: Any = None
        self._response_status = 0
        self._response_sha = ""
        self._readback_sha = ""
        self._verifier_claim_ids: tuple[str, ...] = ()
        self._compensation: tuple[str, str, Any] | None = None

    def _check_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError("HTTP effects require https")
        if (parsed.hostname or "").casefold() not in self.allowed_hosts:
            raise ValueError("HTTP effect host is not allowlisted")

    def prepare(
        self,
        *,
        method: str,
        url: str,
        payload: Any,
        readback_url: str,
        expected_status: int = 200,
        expected_readback: Any | None = None,
        compensation: tuple[str, str, Any] | None = None,
    ) -> HttpActionProposal:
        if self.state is not HttpEffectState.NEW:
            raise RuntimeError("HTTP effect is already prepared")
        method = method.upper()
        if method not in self._METHODS:
            raise ValueError("unsupported mutation method")
        self._check_url(url)
        self._check_url(readback_url)
        if compensation is not None:
            comp_method, comp_url, _ = compensation
            if comp_method.upper() not in self._METHODS:
                raise ValueError("unsupported compensation method")
            self._check_url(comp_url)
        self._payload = payload
        self._compensation = compensation
        self.proposal = HttpActionProposal(
            action_id="http_" + uuid.uuid4().hex[:24],
            method=method,
            url=url,
            readback_url=readback_url,
            expected_status=int(expected_status),
            request_sha256=_sha(payload),
            expected_readback_sha256=_sha(expected_readback) if expected_readback is not None else None,
            reversible=compensation is not None,
        )
        self.state = HttpEffectState.PREPARED
        return self.proposal

    def authorize(self, *, principal: str, authority_ref: str) -> None:
        if self.state is not HttpEffectState.PREPARED:
            raise RuntimeError("HTTP effect must be prepared before authorization")
        if not principal.strip() or not authority_ref.strip():
            raise ValueError("principal and authority_ref must be non-empty")
        self.principal = principal
        self.authority_ref = authority_ref
        self.state = HttpEffectState.AUTHORIZED

    def execute(self) -> None:
        if self.state is not HttpEffectState.AUTHORIZED:
            raise RuntimeError("HTTP effect must be authorized before execution")
        assert self.proposal is not None
        response = self.client.request(self.proposal.method, self.proposal.url, json=self._payload)
        self._response_status = response.status_code
        try:
            body: Any = response.json()
        except ValueError:
            body = {"text": response.text}
        self._response_sha = _sha(body)
        if response.status_code != self.proposal.expected_status:
            raise RuntimeError(f"HTTP effect returned status {response.status_code}, expected {self.proposal.expected_status}")
        self.state = HttpEffectState.EXECUTED

    def readback(self) -> str:
        if self.state is not HttpEffectState.EXECUTED:
            raise RuntimeError("HTTP effect must execute before readback")
        assert self.proposal is not None
        response = self.client.get(self.proposal.readback_url)
        response.raise_for_status()
        try:
            body: Any = response.json()
        except ValueError:
            body = {"text": response.text}
        self._readback_sha = _sha(body)
        expected = self.proposal.expected_readback_sha256
        if expected is not None and self._readback_sha != expected:
            raise RuntimeError("HTTP effect readback does not match expected state")
        self.state = HttpEffectState.READ_BACK
        return self._readback_sha

    def verify(self, graph: ProofGraph, *, claim_ids: list[str] | tuple[str, ...]) -> None:
        if self.state is not HttpEffectState.READ_BACK:
            raise RuntimeError("HTTP effect requires readback before verification")
        ids = tuple(claim_ids)
        if not graph.accepts(ids):
            raise RuntimeError("verification proof missing, stale, revoked, or false")
        expected_subject = f"sha256:{self._readback_sha}"
        if not any(graph.claim(claim_id).subject == expected_subject for claim_id in ids):
            raise RuntimeError("verification proof is not bound to exact HTTP readback")
        self._verifier_claim_ids = ids
        self.state = HttpEffectState.VERIFIED

    def commit(self) -> HttpEffectReceipt:
        if self.state is not HttpEffectState.VERIFIED:
            raise RuntimeError("HTTP effect is not verified")
        self.state = HttpEffectState.COMMITTED
        return self.receipt()

    def compensate(self) -> HttpEffectReceipt:
        if self.state not in {HttpEffectState.EXECUTED, HttpEffectState.READ_BACK, HttpEffectState.VERIFIED}:
            raise RuntimeError("HTTP effect is not in a compensatable state")
        if self._compensation is None:
            raise RuntimeError("no explicit compensation request was prepared")
        method, url, payload = self._compensation
        response = self.client.request(method.upper(), url, json=payload)
        response.raise_for_status()
        self.state = HttpEffectState.COMPENSATED
        return self.receipt()

    def receipt(self) -> HttpEffectReceipt:
        if self.proposal is None:
            raise RuntimeError("HTTP effect has not been prepared")
        return HttpEffectReceipt(
            action_id=self.proposal.action_id,
            method=self.proposal.method,
            url=self.proposal.url,
            state=self.state.value,
            principal=self.principal,
            authority_ref=self.authority_ref,
            response_status=self._response_status,
            response_sha256=self._response_sha,
            readback_sha256=self._readback_sha,
            verifier_claim_ids=self._verifier_claim_ids,
        )
