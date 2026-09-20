"""Detached-GPG signature verification for the DelegationRecord.

Spec §3, §8. This is the root-of-trust check the whole design rests on: the
owner signs the record with a hardware key the agent cannot hold, and the spine
verifies that signature against a committed public key on EVERY signing act.
The agent can verify the owner's hand but can never produce one (decision 2 + 5).

v1 is GPG-only (SSH ``-Y`` deferred, spec §10). gpg 2.4.9 is present on the
owner box and preinstalled on ubuntu-latest CI runners, so no new dependency.

The function is pure verification: it never generates keys and never signs. Key
generation/signing is the owner's out-of-band ceremony (see keys/README.md).
Tests drive it with a throwaway fixture keyring in a temp GNUPGHOME and never
touch the owner's real key or token (spec §9).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import tempfile


@dataclass(frozen=True)
class SignatureResult:
    ok: bool
    reason: str
    signer_fingerprint: str | None = None


def _gpg(homedir: Path, extra: list[str], *, stdin: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    """Run gpg with ``homedir`` as its keyring, pinned via cwd + relative homedir.

    The homedir is passed as ``.`` with the process cwd set to it, NOT as an
    absolute path argument. On the owner's box gpg is an MSYS build, and MSYS
    recognises only a ``/``-prefixed argument as absolute: a Windows ``C:\\...``
    path is joined onto gpg's cwd, the keyring silently resolves to a nonexistent
    nested directory, no agent starts, and every verification fails closed. The
    cwd is set by CreateProcess directly (no shell, no conversion layer), so this
    behaves identically on MSYS and on the Linux CI runners.

    Consequence: every FILE argument must also be relative to ``homedir``.
    """
    cmd = ["gpg", "--batch", "--no-tty", "--yes", "--no-permission-warning",
           "--homedir", ".", *extra]
    return subprocess.run(cmd, input=stdin, capture_output=True, check=False,
                          cwd=str(homedir))


def _trusted_fingerprint(homedir: Path) -> str | None:
    """First (primary) key fingerprint present in the keyring, uppercased."""
    proc = _gpg(homedir, ["--list-keys", "--with-colons"])
    if proc.returncode != 0:
        return None
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        parts = line.split(":")
        # fpr::::::::<FINGERPRINT>:...........
        if len(parts) > 9 and parts[0] == "fpr":
            return parts[9].upper()
    return None


def _parse_validsig(status: str) -> str | None:
    """Extract the full signer fingerprint from a VALIDSIG status line.

    ``[GNUPG:] VALIDSIG <fpr> <date> ...`` -- VALIDSIG is emitted for any good
    signature regardless of ownertrust, so it is the reliable binding signal.
    """
    for line in status.splitlines():
        marker = "[GNUPG:] VALIDSIG "
        if line.startswith(marker):
            fields = line[len(marker):].split()
            if fields:
                return fields[0].upper()
    return None


def verify_detached_signature(
    record_bytes: bytes,
    sig_bytes: bytes,
    pubkey_armored: str,
    *,
    gnupghome: Path | str | None = None,
) -> SignatureResult:
    """Verify a detached GPG signature over ``record_bytes`` against ``pubkey_armored``.

    Returns a SignatureResult. ``ok`` is True only when the signature is good AND
    the signer fingerprint equals the single trusted key imported from
    ``pubkey_armored``. Any other outcome is a fail-closed refusal with a reason
    drawn from the spec §8 taxonomy:

      - signature_missing        : no signature bytes
      - signature_malformed      : gpg could not parse the signature
      - pubkey_unknown           : no/invalid armored pubkey, or import failed
      - signature_key_mismatch   : good sig, but by a key other than the trusted one
      - record_tampered          : BADSIG -- signature does not match the bytes

    When ``gnupghome`` is given, that keyring is used as-is (tests point it at a
    fixture ring that already holds the pubkey). When omitted, an isolated temp
    keyring is created, the trusted pubkey is imported into it, and verification
    runs there -- so only the one committed key can ever satisfy a check.
    """
    if not record_bytes:
        return SignatureResult(False, "record_empty")
    if not sig_bytes:
        return SignatureResult(False, "signature_missing")
    if not pubkey_armored or "BEGIN PGP PUBLIC KEY" not in pubkey_armored:
        return SignatureResult(False, "pubkey_unknown")

    own_home = gnupghome is None
    tmp_home: str | None = None
    if own_home:
        tmp_home = tempfile.mkdtemp(prefix="owner-proxy-gpg-")
        home = Path(tmp_home)
    else:
        home = Path(str(gnupghome))

    try:
        if own_home:
            imp = _gpg(home, ["--import", "-"], stdin=pubkey_armored.encode("utf-8"))
            if imp.returncode != 0:
                return SignatureResult(False, "pubkey_unknown")

        trusted = _trusted_fingerprint(home)
        if trusted is None:
            return SignatureResult(False, "pubkey_unknown")

        # The payload lives INSIDE the keyring dir and is handed to gpg by relative
        # name: _gpg pins the process cwd to the homedir, so an absolute Windows
        # path here would be mangled by MSYS exactly as the homedir argument was.
        (home / "record.bin").write_bytes(record_bytes)
        (home / "record.sig").write_bytes(sig_bytes)

        proc = _gpg(home, ["--status-fd", "1", "--verify", "record.sig", "record.bin"])
        status = proc.stdout.decode("utf-8", "replace")

        signer = _parse_validsig(status)
        if "[GNUPG:] GOODSIG" in status or "[GNUPG:] VALIDSIG" in status:
            if signer is not None and signer != trusted:
                return SignatureResult(False, "signature_key_mismatch", signer)
            return SignatureResult(True, "ok", signer or trusted)
        if "[GNUPG:] BADSIG" in status:
            return SignatureResult(False, "record_tampered", signer)
        if "[GNUPG:] ERRSIG" in status or "[GNUPG:] NO_PUBKEY" in status:
            return SignatureResult(False, "signature_key_mismatch", signer)
        return SignatureResult(False, "signature_malformed", signer)
    finally:
        if tmp_home is not None:
            shutil.rmtree(tmp_home, ignore_errors=True)