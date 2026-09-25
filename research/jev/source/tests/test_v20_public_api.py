import jev_engineering as j


def test_v20_public_api_exports():
    for name in [
        "ExecutionEvent", "ExecutionJournal", "NodeGateway", "NodeGatewayServer",
        "OperationRegistry", "EphemeralCertificateAuthority", "LeaseControlService",
        "SignedProofDelta", "SignedProofReplicator", "DiversityQuorumVerifier", "PreconfiguredVerifierCapability",
        "make_journaled_verification_handler", "validate_execution_journal",
    ]:
        assert hasattr(j, name), name
    assert tuple(map(int, j.__version__.split("."))) >= (2, 8, 0)
