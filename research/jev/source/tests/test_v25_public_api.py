from __future__ import annotations

import jev_engineering as j


def test_v25_public_api_and_version():
    assert tuple(map(int, j.__version__.split("."))) >= (2, 8, 0)
    for name in (
        "EvidenceCampaignPolicy",
        "evaluate_evidence_campaign",
        "analyze_frontier_efficiency_target",
        "ContinuousRegressionMonitor",
        "CampaignEvidenceBundle",
        "plan_noninferiority_pairs",
    ):
        assert hasattr(j, name), name
