from __future__ import annotations

import os
from pathlib import Path

_ALLOWED_ENV_KEYS = {
    "DIALAGRAM_API_KEY": "DIALAGRAM_API_KEY",
    "HERMES_CUSTOM_DIALAGRAM_ME_API_KEY": "DIALAGRAM_API_KEY",
    "NEXUM_API_KEY": "DIALAGRAM_API_KEY",
    "TYPESAFE_API_KEY": "TYPESAFE_API_KEY",
}


def _parse_line(line: str) -> tuple[str, str] | None:
    text = line.strip()
    if not text or text.startswith("#") or "=" not in text:
        return None
    key, value = text.split("=", 1)
    key = key.strip()
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def load_allowed_env_file(
    path: str | Path,
    *,
    override: bool = False,
) -> dict[str, bool]:
    """Load only the credential names this package needs from a dotenv file.

    Secret values are never returned. Hermes' historical custom Dialagram key
    name is mapped to the canonical `DIALAGRAM_API_KEY` expected by this
    package. Existing process values win unless `override=True` is requested.
    """
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)

    found: dict[str, bool] = {}
    for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        parsed = _parse_line(line)
        if parsed is None:
            continue
        source_key, value = parsed
        target_key = _ALLOWED_ENV_KEYS.get(source_key)
        if not target_key or not value:
            continue
        if override or not os.environ.get(target_key):
            os.environ[target_key] = value
        found[target_key] = bool(os.environ.get(target_key))
    return dict(sorted(found.items()))


def hermes_profile_env(profile: str = "avc") -> Path:
    """Return the conventional Windows Hermes profile dotenv path."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is not set; pass an explicit --env-file instead")
    return Path(local_app_data) / "hermes" / "profiles" / profile / ".env"
