from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_REQUIRED = ("metadata", "metrics", "verifier", "stdout", "stderr")


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_run_evidence(root: Path, run_id: str, payloads: dict) -> Path:
    """Atomically create one immutable completed-run evidence directory."""
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("invalid run_id")
    missing = [key for key in _REQUIRED if key not in payloads]
    if missing:
        raise ValueError(f"missing evidence payloads: {', '.join(missing)}")

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / run_id
    if destination.exists():
        raise FileExistsError(destination)

    temp_dir = Path(tempfile.mkdtemp(prefix=f".{run_id}.", dir=root))
    try:
        files = {
            "metadata.json": ("json", payloads["metadata"]),
            "metrics.json": ("json", payloads["metrics"]),
            "verifier.json": ("json", payloads["verifier"]),
            "stdout.log": ("text", str(payloads["stdout"])),
            "stderr.log": ("text", str(payloads["stderr"])),
        }
        for name, (kind, value) in files.items():
            path = temp_dir / name
            if kind == "json":
                _write_json(path, value)
            else:
                path.write_text(value, encoding="utf-8")

        manifest_lines = [f"{_sha256(temp_dir / name)}  {name}" for name in sorted(files)]
        (temp_dir / "artifacts.sha256").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
        temp_dir.rename(destination)
        return destination
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
