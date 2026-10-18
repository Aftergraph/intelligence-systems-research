from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from typing import Mapping

SECRET_ALIASES: dict[str, str] = {
    "DIALAGRAM_API_KEY": "DIALAGRAM_API_KEY",
    "HERMES_CUSTOM_DIALAGRAM_ME_API_KEY": "DIALAGRAM_API_KEY",
    "NEXUM_API_KEY": "DIALAGRAM_API_KEY",
    "TYPESAFE_API_KEY": "TYPESAFE_API_KEY",
}


@dataclass(frozen=True, slots=True)
class SecretStatus:
    name: str
    present: bool
    source: str
    fingerprint: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "present": self.present,
            "source": self.source,
            "fingerprint": self.fingerprint,
        }


def secret_fingerprint(value: str) -> str:
    """Non-secret correlation identifier; never use as authentication material."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key in SECRET_ALIASES and value:
            values[SECRET_ALIASES[key]] = value
    return values


class SecretResolver:
    """Resolve only explicitly allowed credentials without ever serializing values.

    Resolution order is process environment first, then an optional dotenv file.
    In GitHub Actions the workflow injects encrypted GitHub Secrets as environment
    variables, so the runtime uses the same code path locally and in CI.
    """

    def __init__(self, *, env_file: str | Path | None = None) -> None:
        self.env_file = Path(env_file).expanduser().resolve() if env_file else None
        self._file_values = _parse_dotenv(self.env_file) if self.env_file else {}

    def get(self, name: str) -> str:
        canonical = SECRET_ALIASES.get(name, name)
        if canonical not in set(SECRET_ALIASES.values()):
            raise KeyError(f"secret {name!r} is not allowlisted")
        value = os.environ.get(canonical, "")
        if value:
            return value
        value = self._file_values.get(canonical, "")
        if value:
            return value
        raise RuntimeError(f"required secret {canonical} is not configured")

    def status(self, name: str, *, include_fingerprint: bool = False) -> SecretStatus:
        canonical = SECRET_ALIASES.get(name, name)
        if canonical not in set(SECRET_ALIASES.values()):
            raise KeyError(f"secret {name!r} is not allowlisted")
        value = os.environ.get(canonical, "")
        source = "process_env"
        if not value:
            value = self._file_values.get(canonical, "")
            source = "dotenv" if value else "missing"
        return SecretStatus(
            name=canonical,
            present=bool(value),
            source=source,
            fingerprint=secret_fingerprint(value) if include_fingerprint and value else None,
        )

    def materialize_to_process(self, names: tuple[str, ...] = ("DIALAGRAM_API_KEY", "TYPESAFE_API_KEY")) -> list[SecretStatus]:
        statuses: list[SecretStatus] = []
        for name in names:
            canonical = SECRET_ALIASES.get(name, name)
            if os.environ.get(canonical):
                statuses.append(self.status(canonical))
                continue
            value = self._file_values.get(canonical, "")
            if value:
                os.environ[canonical] = value
            statuses.append(self.status(canonical))
        return statuses


def write_private_env(path: str | Path, values: Mapping[str, str]) -> Path:
    """Write an explicitly local-only dotenv with owner-only permissions.

    The caller must keep this file outside release artifacts and source control.
    """
    target = Path(path).expanduser().resolve()
    canonical: dict[str, str] = {}
    for key, value in values.items():
        name = SECRET_ALIASES.get(key, key)
        if name not in set(SECRET_ALIASES.values()):
            raise KeyError(f"secret {key!r} is not allowlisted")
        if not value:
            raise ValueError(f"secret {name} is empty")
        canonical[name] = value
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(f"{key}={value}\n" for key, value in sorted(canonical.items()))
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, payload.encode("utf-8"))
    finally:
        os.close(fd)
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    return target
