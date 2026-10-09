from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import ipaddress
from pathlib import Path
from typing import Iterable

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


@dataclass(frozen=True, slots=True)
class PemIdentity:
    certificate_pem: bytes
    private_key_pem: bytes
    ca_certificate_pem: bytes

    def write(self, directory: str | Path, *, prefix: str) -> tuple[Path, Path, Path]:
        root = Path(directory)
        root.mkdir(parents=True, exist_ok=True)
        cert = root / f"{prefix}.crt.pem"
        key = root / f"{prefix}.key.pem"
        ca = root / "ca.crt.pem"
        cert.write_bytes(self.certificate_pem)
        key.write_bytes(self.private_key_pem)
        ca.write_bytes(self.ca_certificate_pem)
        try:
            key.chmod(0o600)
        except OSError:
            pass
        return cert, key, ca


class EphemeralCertificateAuthority:
    """Small PKI helper for local/reference deployments and tests.

    Production deployments should use an organization-managed CA/SPIFFE/OIDC
    identity plane rather than persisting this generated CA.
    """

    def __init__(self, *, common_name: str = "Aftergraph Reference CA") -> None:
        self._key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
        now = datetime.now(timezone.utc)
        self._cert = (
            x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(self._key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(days=7))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=False, content_commitment=False, key_encipherment=False, data_encipherment=False, key_agreement=False, key_cert_sign=True, crl_sign=True, encipher_only=False, decipher_only=False), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(self._key.public_key()), critical=False)
            .sign(self._key, hashes.SHA256())
        )

    @property
    def ca_pem(self) -> bytes:
        return self._cert.public_bytes(serialization.Encoding.PEM)

    def issue(
        self,
        *,
        common_name: str,
        dns_names: Iterable[str] = (),
        ip_addresses: Iterable[str] = (),
        server: bool = False,
        client: bool = False,
        ttl: timedelta = timedelta(hours=1),
    ) -> PemIdentity:
        if not common_name.strip() or ttl.total_seconds() <= 0:
            raise ValueError("common_name and positive ttl are required")
        if not server and not client:
            raise ValueError("certificate must be server and/or client capable")
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = datetime.now(timezone.utc)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject).issuer_name(self._cert.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + ttl)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=True, data_encipherment=False, key_agreement=False, key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(self._key.public_key()), critical=False)
        )
        sans: list[x509.GeneralName] = [x509.DNSName(v) for v in dns_names]
        sans.extend(x509.IPAddress(ipaddress.ip_address(v)) for v in ip_addresses)
        if sans:
            builder = builder.add_extension(x509.SubjectAlternativeName(sans), critical=False)
        eku = []
        if server:
            eku.append(ExtendedKeyUsageOID.SERVER_AUTH)
        if client:
            eku.append(ExtendedKeyUsageOID.CLIENT_AUTH)
        builder = builder.add_extension(x509.ExtendedKeyUsage(eku), critical=False)
        cert = builder.sign(self._key, hashes.SHA256())
        return PemIdentity(
            certificate_pem=cert.public_bytes(serialization.Encoding.PEM),
            private_key_pem=key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ),
            ca_certificate_pem=self.ca_pem,
        )
