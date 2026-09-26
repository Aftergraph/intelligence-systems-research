from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import os
from pathlib import Path
import tempfile
import uuid

from .proof_graph import ProofGraph


def _digest(data: bytes | None) -> str:
    return "missing" if data is None else hashlib.sha256(data).hexdigest()


class EffectState(str, Enum):
    NEW = "new"
    PREPARED = "prepared"
    AUTHORIZED = "authorized"
    SPECULATING = "speculating"
    EXECUTED = "executed"
    READ_BACK = "read_back"
    VERIFIED = "verified"
    COMMITTED = "committed"
    COMPENSATED = "compensated"


@dataclass(frozen=True, slots=True)
class ActionProposal:
    action_id: str
    kind: str
    target: str
    expected_effect: str
    reversible: bool
    preimage_sha256: str
    proposed_sha256: str


@dataclass(frozen=True, slots=True)
class EffectReadback:
    action_id: str
    observed_sha256: str
    expected_sha256: str
    matches_expected: bool


@dataclass(frozen=True, slots=True)
class EffectReceipt:
    action_id: str
    kind: str
    target: str
    state: str
    principal: str
    authority_ref: str
    preimage_sha256: str
    postimage_sha256: str
    readback_sha256: str
    verifier_claim_ids: tuple[str, ...]
    compensated_to_sha256: str | None = None


class FileEffectTransaction:
    """Reversible repository-file effect transaction.

    This v1 adapter is intentionally file-only. It demonstrates the full
    PREPARE -> AUTHORIZE -> SPECULATE -> EXECUTE -> READBACK -> VERIFY ->
    COMMIT/COMPENSATE contract without pretending arbitrary shell, network,
    deployment, IAM, billing, or email effects are reversible.
    """

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).resolve()
        if not self.workspace.is_dir():
            raise ValueError("workspace must be an existing directory")
        self.state = EffectState.NEW
        self.proposal: ActionProposal | None = None
        self.principal = ""
        self.authority_ref = ""
        self._target: Path | None = None
        self._preimage: bytes | None = None
        self._postimage: bytes | None = None
        self._readback_sha = ""
        self._verifier_claim_ids: tuple[str, ...] = ()
        self._tmp = tempfile.TemporaryDirectory(prefix="jev-effect-")
        self._staged = Path(self._tmp.name) / "staged.bin"

    def _resolve(self, relative_path: str) -> tuple[Path, str]:
        rel = Path(relative_path)
        if rel.is_absolute() or ".." in rel.parts or not rel.parts:
            raise ValueError("effect path must remain inside workspace")
        target = (self.workspace / rel).resolve()
        try:
            target.relative_to(self.workspace)
        except ValueError as exc:
            raise ValueError("effect path must remain inside workspace") from exc
        return target, rel.as_posix()

    def _require(self, *states: EffectState) -> None:
        if self.state not in states:
            allowed = ", ".join(state.value for state in states)
            raise RuntimeError(f"effect state {self.state.value!r} does not allow operation; expected {allowed}")

    def prepare(self, relative_path: str, content: str | bytes, *, expected_effect: str) -> ActionProposal:
        self._require(EffectState.NEW)
        if not expected_effect.strip():
            raise ValueError("expected_effect must be non-empty")
        target, rel = self._resolve(relative_path)
        preimage = target.read_bytes() if target.exists() else None
        postimage = content.encode("utf-8") if isinstance(content, str) else bytes(content)
        self._staged.write_bytes(postimage)
        self._target = target
        self._preimage = preimage
        self._postimage = postimage
        self.proposal = ActionProposal(
            action_id="act_" + uuid.uuid4().hex[:24],
            kind="file_write",
            target=rel,
            expected_effect=expected_effect,
            reversible=True,
            preimage_sha256=_digest(preimage),
            proposed_sha256=_digest(postimage),
        )
        self.state = EffectState.PREPARED
        return self.proposal

    def authorize(self, *, principal: str, authority_ref: str) -> None:
        self._require(EffectState.PREPARED)
        if not principal.strip() or not authority_ref.strip():
            raise ValueError("principal and authority_ref must be non-empty")
        self.principal = principal
        self.authority_ref = authority_ref
        self.state = EffectState.AUTHORIZED

    def speculate(self) -> ActionProposal:
        self._require(EffectState.AUTHORIZED)
        assert self.proposal is not None
        self.state = EffectState.SPECULATING
        return self.proposal

    def execute(self) -> None:
        self._require(EffectState.SPECULATING)
        assert self._target is not None and self._postimage is not None and self.proposal is not None
        current = self._target.read_bytes() if self._target.exists() else None
        if _digest(current) != self.proposal.preimage_sha256:
            raise RuntimeError("workspace drift before effect execution")
        self._target.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._target.with_name(self._target.name + ".jev-effect.tmp")
        tmp.write_bytes(self._staged.read_bytes())
        os.replace(tmp, self._target)
        self.state = EffectState.EXECUTED

    def readback(self) -> EffectReadback:
        self._require(EffectState.EXECUTED)
        assert self._target is not None and self.proposal is not None
        observed = self._target.read_bytes() if self._target.exists() else None
        observed_sha = _digest(observed)
        expected_sha = self.proposal.proposed_sha256
        self._readback_sha = observed_sha
        if observed_sha != expected_sha:
            raise RuntimeError("effect readback does not match proposed effect")
        self.state = EffectState.READ_BACK
        return EffectReadback(self.proposal.action_id, observed_sha, expected_sha, True)

    def verify(self, proof_graph: ProofGraph, *, claim_ids: list[str] | tuple[str, ...]) -> None:
        self._require(EffectState.READ_BACK)
        ids = tuple(claim_ids)
        try:
            accepted = proof_graph.accepts(ids)
        except KeyError:
            accepted = False
        if not accepted:
            raise RuntimeError("verification proof missing, stale, revoked, or false")
        assert self.proposal is not None
        # Bind at least one accepted claim to the exact post-effect subject.
        expected_subject = f"sha256:{self.proposal.proposed_sha256}"
        if not any(proof_graph.claim(claim_id).subject == expected_subject for claim_id in ids):
            raise RuntimeError("verification proof is not bound to exact effect subject")
        self._verifier_claim_ids = ids
        self.state = EffectState.VERIFIED

    def commit(self) -> EffectReceipt:
        self._require(EffectState.VERIFIED)
        assert self._target is not None and self.proposal is not None
        current = self._target.read_bytes() if self._target.exists() else None
        if _digest(current) != self.proposal.proposed_sha256:
            raise RuntimeError("workspace drift after verification; refusing commit")
        self.state = EffectState.COMMITTED
        return self.receipt()

    def compensate(self) -> EffectReceipt:
        self._require(EffectState.EXECUTED, EffectState.READ_BACK, EffectState.VERIFIED)
        assert self._target is not None and self.proposal is not None
        current = self._target.read_bytes() if self._target.exists() else None
        if _digest(current) != self.proposal.proposed_sha256:
            raise RuntimeError("workspace drift prevents safe compensation")
        if self._preimage is None:
            self._target.unlink(missing_ok=True)
        else:
            tmp = self._target.with_name(self._target.name + ".jev-compensate.tmp")
            tmp.write_bytes(self._preimage)
            os.replace(tmp, self._target)
        self.state = EffectState.COMPENSATED
        return self.receipt(compensated_to_sha256=_digest(self._preimage))

    def receipt(self, *, compensated_to_sha256: str | None = None) -> EffectReceipt:
        if self.proposal is None:
            raise RuntimeError("effect has not been prepared")
        return EffectReceipt(
            action_id=self.proposal.action_id,
            kind=self.proposal.kind,
            target=self.proposal.target,
            state=self.state.value,
            principal=self.principal,
            authority_ref=self.authority_ref,
            preimage_sha256=self.proposal.preimage_sha256,
            postimage_sha256=self.proposal.proposed_sha256,
            readback_sha256=self._readback_sha,
            verifier_claim_ids=self._verifier_claim_ids,
            compensated_to_sha256=compensated_to_sha256,
        )

    def close(self) -> None:
        self._tmp.cleanup()

    def __enter__(self) -> "FileEffectTransaction":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
