"""Tests for research metrics receipt v0.1."""
import json
from pathlib import Path
import pytest
from src.research_metrics import calculate, validate

ROOT = Path(__file__).resolve().parent.parent

def _receipt():
    return {
      "schema_version":"aftergraph.research.metrics.v0.1","receipt_id":"r1","study_id":"S1",
      "run_set_ref":"runs:1","population":"registered runs","window":{"start":"2026-09-18T00:00:00Z","end":"2026-09-18T01:00:00Z"},
      "counters":{"verifiable_claims":10,"deterministically_verified_claims":8,"verified_claims":8,"judge_only_verified_claims":1,"independently_verified_claims":6,"replication_attempts":4,"replication_successes":3,"falsification_attempts":5,"reproducible_counterexamples":2,"applicable_adversarial_classes":8,"covered_adversarial_classes":7,"research_progress_events":3},
      "resources":{"tokens":6000,"wall_clock_seconds":7200,"cost_usd":12.0,"human_interventions":2},
      "provenance":{"source_commit":"abcdef1","evidence_refs":["e1"],"verifier_refs":["v1"],"generated_at":"2026-09-18T01:00:00Z"}
    }

def test_calculates_canonical_headline_metrics():
    m=calculate(_receipt())
    assert m["dvcr"] == pytest.approx(.8)
    assert m["jcr"] == pytest.approx(.125)
    assert m["ivcr"] == pytest.approx(.75)
    assert m["replication_success_rate"] == pytest.approx(.75)
    assert m["falsification_yield"] == pytest.approx(.4)
    assert m["adversarial_coverage"] == pytest.approx(.875)
    assert m["verified_progress_per_cost_usd"] == pytest.approx(.25)
    assert m["verified_progress_per_1k_tokens"] == pytest.approx(.5)
    assert m["verified_progress_per_hour"] == pytest.approx(1.5)

def test_zero_denominator_is_unknown_not_zero():
    r=_receipt()
    for k in ["verifiable_claims","verified_claims","replication_attempts","falsification_attempts","applicable_adversarial_classes"]:
        r["counters"][k]=0
    for k in ["deterministically_verified_claims","judge_only_verified_claims","independently_verified_claims","replication_successes","reproducible_counterexamples","covered_adversarial_classes"]:
        r["counters"][k]=0
    r["resources"].update(tokens=None,cost_usd=None,wall_clock_seconds=0)
    m=calculate(r)
    assert all(m[k] is None for k in ["dvcr","jcr","ivcr","replication_success_rate","falsification_yield","adversarial_coverage","verified_progress_per_cost_usd","verified_progress_per_1k_tokens","verified_progress_per_hour"])

def test_impossible_subset_counts_fail_closed():
    r=_receipt(); r["counters"]["judge_only_verified_claims"]=9
    with pytest.raises(ValueError): validate(r)

def test_baseline_refuses_to_invent_research_metrics():
    r=json.loads((ROOT/"data/research_metrics_baseline_v02.json").read_text(encoding="utf-8"))
    m=calculate(r)
    assert r["counters"]["research_progress_events"] == 0
    assert m["dvcr"] is None and m["jcr"] is None and m["ivcr"] is None
    assert m["verified_progress_per_cost_usd"] is None
