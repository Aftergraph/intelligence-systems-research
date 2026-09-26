from __future__ import annotations

import jev_engineering as j


def test_v24_public_api_and_version():
    assert tuple(map(int, j.__version__.split("."))) >= (2, 8, 0)
    for name in (
        "RelayGenerationStore", "JournalCheckpointStore", "ResumableJournalFollower",
        "TokenPrice", "BenchmarkCostModel", "build_campaign_report",
        "PhysicalPairManifest", "generate_physical_pair_template",
    ):
        assert hasattr(j, name), name
