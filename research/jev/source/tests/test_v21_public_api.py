import jev_engineering as j


def test_v21_public_api_exports():
    for name in [
        "JournalPage", "JournalStreamRegistry", "JournalStreamService", "verify_journal_pages",
        "MissionMeasurement", "ConditionMetrics", "summarize_measurements",
        "paired_frontier_efficiency_ratio", "MultiNodeResult",
        "MultiNodeVerificationCoordinator", "RemoteVerifierTarget",
    ]:
        assert hasattr(j, name), name
    assert tuple(map(int, j.__version__.split("."))) >= (2, 8, 0)
