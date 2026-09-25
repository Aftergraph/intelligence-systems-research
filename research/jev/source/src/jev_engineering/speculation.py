from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import tempfile

from .proof_graph import ProofGraph


def _digest(data: bytes | None) -> str:
    if data is None:
        return "missing"
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True, slots=True)
class StagedFileWrite:
    relative_path: str
    preimage_sha256: str
    staged_sha256: str


class SpeculativeFileTransaction:
    """File-only speculative execution with delayed proof-gated commit.

    Staged writes are isolated in a temporary directory. Commit is fail-closed on
    missing/stale prerequisite proof or workspace drift since staging. This is not
    a sandbox for arbitrary shell/network effects.
    """

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).resolve()
        if not self.workspace.is_dir():
            raise ValueError("workspace must be an existing directory")
        self._tmp = tempfile.TemporaryDirectory(prefix="jev-speculative-")
        self.staging_root = Path(self._tmp.name)
        self._writes: dict[str, StagedFileWrite] = {}
        self._committed = False

    def _resolve(self, relative_path: str) -> tuple[Path, Path, str]:
        rel = Path(relative_path)
        if rel.is_absolute() or ".." in rel.parts or not rel.parts:
            raise ValueError("path must remain inside workspace")
        target = (self.workspace / rel).resolve()
        try:
            target.relative_to(self.workspace)
        except ValueError as exc:
            raise ValueError("path must remain inside workspace") from exc
        staged = self.staging_root / rel
        return target, staged, rel.as_posix()

    def stage_write(self, relative_path: str, content: str | bytes) -> StagedFileWrite:
        if self._committed:
            raise RuntimeError("transaction is already committed")
        target, staged, rel = self._resolve(relative_path)
        current = target.read_bytes() if target.exists() else None
        data = content.encode("utf-8") if isinstance(content, str) else bytes(content)
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(data)
        write = StagedFileWrite(rel, _digest(current), _digest(data))
        self._writes[rel] = write
        return write

    def manifest(self) -> dict[str, object]:
        return {
            "version": 1,
            "state": "committed" if self._committed else "staged",
            "writes": [
                {
                    "path": write.relative_path,
                    "preimage_sha256": write.preimage_sha256,
                    "staged_sha256": write.staged_sha256,
                }
                for write in sorted(self._writes.values(), key=lambda item: item.relative_path)
            ],
        }

    def commit(
        self,
        proof_graph: ProofGraph,
        *,
        prerequisite_claim_ids: tuple[str, ...] | list[str],
    ) -> list[str]:
        if self._committed:
            raise RuntimeError("transaction is already committed")
        prerequisites = tuple(prerequisite_claim_ids)
        try:
            accepted = proof_graph.accepts(prerequisites)
        except KeyError:
            accepted = False
        if not accepted:
            raise RuntimeError("prerequisite proof is missing, stale, revoked, or false")

        for rel, write in self._writes.items():
            target, _, _ = self._resolve(rel)
            current = target.read_bytes() if target.exists() else None
            if _digest(current) != write.preimage_sha256:
                raise RuntimeError(f"preimage changed for speculative file {rel!r}")

        committed: list[str] = []
        for rel in sorted(self._writes):
            target, staged, _ = self._resolve(rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            temp_target = target.with_name(target.name + ".jev-speculative.tmp")
            temp_target.write_bytes(staged.read_bytes())
            os.replace(temp_target, target)
            committed.append(rel)
        self._committed = True
        return committed

    def close(self) -> None:
        self._tmp.cleanup()

    def __enter__(self) -> "SpeculativeFileTransaction":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
