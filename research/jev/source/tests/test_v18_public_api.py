import jev_engineering as j


def test_v18_public_api_surface_is_importable() -> None:
    for name in [
        "WorksExecutionContext", "Ed25519WorkloadIssuer", "WorkloadIdentityVerifier",
        "Ed25519ReceiptSigner", "Ed25519ReceiptVerifier", "SqliteLeaseStore",
        "SqliteProofGraphStore", "QuorumVerifier", "CircuitBreakerRegistry",
        "TrustGatewayValidator", "WorkerDirectory", "NetworkedMissionRuntime",
    ]:
        assert getattr(j, name)
    assert tuple(map(int, j.__version__.split("."))) >= (1, 8, 0)
