import jev_engineering as jev


def test_v29_public_api():
    assert jev.AuthenticatedLiveHoldoutRunner
    assert jev.LiveCampaignEvidenceBundle
    assert jev.ProviderExecutionAttestation
    assert jev.SignedProviderExecution
    assert tuple(map(int, jev.__version__.split("."))) >= (2, 9, 0)
