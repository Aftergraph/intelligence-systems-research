import jev_engineering as jev


def test_v28_public_api_and_version():
    assert tuple(map(int, jev.__version__.split("."))) >= (2, 8, 0)
    assert jev.PairedHoldoutCampaignRunner
    assert jev.PairedCampaignExecution
    assert jev.PairedMission
