"""Derive a v0.1 research-metrics receipt from frozen STUDY-011 evidence.

Conservative mapping: only counters directly supported by the frozen dataset are
populated. Unsupported R1/R2/replication counters remain zero-denominator and
therefore derive to UNKNOWN, never 0%.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SUMMARY=ROOT/"data/study011_runs/confirmatory/canonical-run-002-analysis/summary.md"
FREEZE=ROOT/"STUDY-011-AMENDMENT-011-POST-EXECUTION-FREEZE.md"

def build() -> dict:
    s=SUMMARY.read_text(encoding="utf-8")
    f=FREEZE.read_text(encoding="utf-8")
    assert "Attempted: 470" in s
    assert "LIVE_VALID total: 470" in s
    assert "All cells >= 58 LIVE_VALID: True" in s
    assert "H1: REVERSED" in s and "H2: SUPPORTED" in s and "H3: REVERSED" in s
    assert "470 LIVE_VALID, 8/8 cells" in f
    # Three preregistered hypotheses reached frozen research verdicts. This is
    # research progress under ISE-R3; it does NOT imply R1 deterministic-claim
    # coverage, independent replication, or the new R2 class coverage.
    return {
      "schema_version":"aftergraph.research.metrics.v0.1",
      "receipt_id":"study011-posthoc-v02-20260918",
      "study_id":"STUDY-011",
      "run_set_ref":"data/study011_runs/confirmatory/canonical-run-002/",
      "population":"Frozen STUDY-011 canonical-run-002 analysis view: 470 LIVE_VALID records, 8/8 cells >=58. Post-hoc v0.2 metric projection; no new empirical run.",
      "window":{"start":"2026-09-04T00:00:00Z","end":"2026-09-04T17:23:00Z"},
      "counters":{
        "verifiable_claims":0,"deterministically_verified_claims":0,
        "verified_claims":0,"judge_only_verified_claims":0,
        "independently_verified_claims":0,
        "replication_attempts":0,"replication_successes":0,
        "falsification_attempts":3,"reproducible_counterexamples":2,
        "applicable_adversarial_classes":0,"covered_adversarial_classes":0,
        "research_progress_events":3
      },
      "resources":{"tokens":None,"wall_clock_seconds":None,"cost_usd":None,"human_interventions":None},
      "provenance":{
        "source_commit":"06d906bcab0159527e76fc866bb7c74ac294f32f",
        "evidence_refs":[
          "data/study011_runs/confirmatory/canonical-run-002-analysis/summary.md",
          "data/study011_runs/confirmatory/canonical-run-002-analysis/FINAL-CONFIRMATORY-SUMMARY.md",
          "STUDY-011-AMENDMENT-011-POST-EXECUTION-FREEZE.md"
        ],
        "verifier_refs":["experiments/live_benchmark/study011_analyze.py"],
        "generated_at":"2026-09-18T11:55:00Z"
      }
    }

if __name__=="__main__":
    print(json.dumps(build(),indent=2))
