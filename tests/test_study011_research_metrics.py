from src.study011_research_metrics import build
from src.research_metrics import calculate

def test_study011_projection_is_evidence_conservative():
    r=build(); m=calculate(r)
    assert r["counters"]["research_progress_events"] == 3
    assert r["counters"]["falsification_attempts"] == 3
    assert r["counters"]["reproducible_counterexamples"] == 2
    assert m["falsification_yield"] == 2/3
    # No retroactive invention of v0.2 measurements from a v0.1-era study.
    assert m["dvcr"] is None
    assert m["jcr"] is None
    assert m["ivcr"] is None
    assert m["replication_success_rate"] is None
    assert m["adversarial_coverage"] is None
    assert m["verified_progress_per_cost_usd"] is None
