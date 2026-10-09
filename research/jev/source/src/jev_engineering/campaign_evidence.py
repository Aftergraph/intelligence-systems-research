from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class CampaignEvidenceBundle:
    path: Path
    payload: dict[str, Any]

    @classmethod
    def create(
        cls,
        *,
        manifest: Path,
        pricing: Path,
        results: Path,
        report: Path,
        output: Path,
        package_version: str,
    ) -> "CampaignEvidenceBundle":
        base = output.resolve().parent
        files = {}
        for name, path in {
            "manifest": manifest,
            "pricing": pricing,
            "results": results,
            "report": report,
        }.items():
            resolved = path.resolve()
            try:
                rel = resolved.relative_to(base)
                stored = str(rel)
            except ValueError:
                stored = str(resolved)
            files[name] = {"path": stored, "sha256": _sha256(resolved)}
        core = {
            "version": 1,
            "package_version": package_version,
            "created_at": datetime.now(UTC).isoformat(),
            "files": files,
        }
        core["bundle_sha256"] = hashlib.sha256(_canonical(core)).hexdigest()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(core, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return cls(output.resolve(), core)

    @classmethod
    def load(cls, path: Path) -> "CampaignEvidenceBundle":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("campaign evidence bundle must be a JSON object")
        return cls(path.resolve(), payload)

    def verify(self, *, base_dir: Path | None = None) -> dict[str, Any]:
        payload = dict(self.payload)
        observed_bundle_hash = str(payload.pop("bundle_sha256", ""))
        expected_bundle_hash = hashlib.sha256(_canonical(payload)).hexdigest()
        mismatches: list[str] = []
        if observed_bundle_hash != expected_bundle_hash:
            mismatches.append("bundle")
        root = (base_dir or self.path.parent).resolve()
        for name, spec in dict(payload.get("files") or {}).items():
            raw_path = Path(str(spec.get("path") or ""))
            path = raw_path if raw_path.is_absolute() else root / raw_path
            if not path.is_file() or _sha256(path) != str(spec.get("sha256") or ""):
                mismatches.append(str(name))
        return {
            "valid": not mismatches,
            "mismatches": sorted(set(mismatches)),
            "bundle_sha256": observed_bundle_hash,
            "package_version": payload.get("package_version"),
        }
