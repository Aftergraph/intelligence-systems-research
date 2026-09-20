"""Throwaway GPG fixture keyring + signed-root installer for owner-proxy tests.

Spec §9: every automated test uses a FIXTURE key generated in a temp GNUPGHOME and
NEVER touches the owner's real key or hardware token. The real signing path is
untestable by the agent by construction (the agent cannot hold the token); these
helpers exist so the VERIFIER side is exercised end to end without ever needing the
owner's hand.

Not a test module (no ``test_`` prefix), so pytest does not collect it; import the
``FixtureKeyring`` class, the ``install_signed_root`` / ``write_signed_revocation``
helpers and the ``fixture_keyring`` pytest fixture from test files.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest

FIXTURE_UID = "Owner-Proxy Test Fixture <fixture@owner-proxy.test>"


def _gpg(homedir: Path, *args: str, stdin: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    """Run gpg with ``homedir`` as GNUPGHOME, pinned via cwd + relative homedir.

    Mirrors ``authority.owner_proxy.signature._gpg`` (single source of the
    workaround): this box's gpg is an MSYS build that treats a Windows
    ``C:\\...`` argument as relative to its cwd, so an absolute homedir silently
    resolves to a nonexistent nested directory and the keyring never initialises.
    Extra FILE arguments must therefore be relative to ``homedir``.
    """
    cmd = [
        "gpg", "--batch", "--no-tty", "--yes", "--no-permission-warning",
        "--homedir", ".", *args,
    ]
    return subprocess.run(cmd, input=stdin, capture_output=True, check=False,
                          cwd=str(homedir))


class FixtureKeyring:
    """A temporary GPG keyring holding ONE freshly generated ed25519 sign key."""

    def __init__(self, homedir: Path, fingerprint: str) -> None:
        self.homedir = homedir
        self.fingerprint = fingerprint

    @classmethod
    def create(cls) -> "FixtureKeyring":
        home = Path(tempfile.mkdtemp(prefix="owner-proxy-fixture-gpg-"))
        try:
            gen = _gpg(
                home,
                "--pinentry-mode", "loopback", "--passphrase", "",
                "--quick-generate-key", FIXTURE_UID, "ed25519", "sign", "never",
            )
            if gen.returncode != 0:
                raise RuntimeError(
                    "fixture keygen failed: " + gen.stderr.decode("utf-8", "replace")
                )
            fpr = cls._first_fingerprint(home)
            if not fpr:
                raise RuntimeError("fixture keygen produced no fingerprint")
            return cls(home, fpr)
        except BaseException:
            shutil.rmtree(home, ignore_errors=True)
            raise

    @staticmethod
    def _first_fingerprint(home: Path) -> str | None:
        proc = _gpg(home, "--list-keys", "--with-colons")
        for line in proc.stdout.decode("utf-8", "replace").splitlines():
            parts = line.split(":")
            if len(parts) > 9 and parts[0] == "fpr":
                return parts[9].upper()
        return None

    def pubkey_armored(self) -> str:
        proc = _gpg(self.homedir, "--armor", "--export", self.fingerprint)
        if proc.returncode != 0 or not proc.stdout:
            raise RuntimeError("fixture pubkey export failed")
        return proc.stdout.decode("utf-8", "replace")

    def sign_bytes(self, data: bytes) -> bytes:
        """Detached binary signature over EXACTLY ``data`` (the bytes we hand gpg).

        Payload and signature live INSIDE the keyring dir and are passed by
        relative name, because _gpg pins the process cwd to the homedir and MSYS
        would mangle an absolute Windows path.
        """
        payload = self.homedir / "fixture_payload.bin"
        out = self.homedir / "fixture_payload.sig"
        try:
            payload.write_bytes(data)
            proc = _gpg(
                self.homedir,
                "--pinentry-mode", "loopback", "--passphrase", "",
                "--detach-sign", "--local-user", self.fingerprint,
                "--output", out.name, payload.name,
            )
            if proc.returncode != 0 or not out.exists():
                raise RuntimeError(
                    "fixture sign failed: " + proc.stderr.decode("utf-8", "replace")
                )
            return out.read_bytes()
        finally:
            payload.unlink(missing_ok=True)
            out.unlink(missing_ok=True)

    def close(self) -> None:
        shutil.rmtree(self.homedir, ignore_errors=True)


def install_signed_root(
    keys_dir: Path | str,
    record_bytes: bytes,
    keyring: FixtureKeyring | None = None,
) -> FixtureKeyring:
    """Materialise a VERIFIED delegation root in ``keys_dir`` using a fixture key.

    Order matters: the record file is written FIRST and the detached signature is
    taken over those exact on-disk bytes, so ``verify_detached_signature`` reads
    back the same bytes it signs. Writing .sig over a re-serialized dict would
    surface as ``record_tampered`` on the happy path.

    Returns the keyring that signed it (the caller closes it, or passes one in to
    reuse across several roots).
    """
    keys_dir = Path(keys_dir)
    keys_dir.mkdir(parents=True, exist_ok=True)
    kr = keyring if keyring is not None else FixtureKeyring.create()
    (keys_dir / "delegation_record.json").write_bytes(record_bytes)
    (keys_dir / "delegation_record.sig").write_bytes(kr.sign_bytes(record_bytes))
    (keys_dir / "owner.pub.asc").write_text(kr.pubkey_armored(), encoding="utf-8")
    return kr


def write_signed_revocation(
    keys_dir: Path | str,
    name: str,
    payload: dict[str, Any],
    keyring: FixtureKeyring,
) -> Path:
    """Write ``keys_dir/<name>.json`` + ``<name>.json.sig`` signed by ``keyring``.

    Matches ``revocation._load_signed_json``'s primary convention
    (``path.with_suffix(path.suffix + ".sig")``). Returns the record path.
    """
    keys_dir = Path(keys_dir)
    keys_dir.mkdir(parents=True, exist_ok=True)
    record_path = keys_dir / f"{name}.json"
    data = (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    record_path.write_bytes(data)
    (keys_dir / f"{name}.json.sig").write_bytes(keyring.sign_bytes(data))
    return record_path


@pytest.fixture(scope="module")
def fixture_keyring():
    kr = FixtureKeyring.create()
    try:
        yield kr
    finally:
        kr.close()
