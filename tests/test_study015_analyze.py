import copy
import json
from pathlib import Path

from experiments.study015.analyze import (
    analyze,
    condition_stats,
    mcnemar_exact,
    pair_conditions,
    paired_continuous,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "study015_fixtures" / "valid_envelope.json"


def row(run_id, condition, verified, *, cost=1.0, ttv=100.0, human=0):
    r = json.loads(FIXTURE.read_text(encoding="utf-8"))
    r.update(run_id=run_id, condition=condition, execution_class="DRY_RUN", is_live=False)
    r["outcome"].update(
        declared_complete=True,
        verified_success=verified,
        false_completion=not verified,
        abstained=False,
        human_interventions=human,
    )
    r["verification"].update(
        independent=verified,
        verifier_id="v" if verified else None,
        verification_subject="s" if verified else None,
        evidence_root="e" if verified else None,
        verdict="PASS" if verified else "NOT_RUN",
    )
    r["performance"]["total_cost_usd"] = cost
    r["performance"]["time_to_verified_ms"] = ttv if verified else None
    return r


def test_condition_stats_computes_vector_metrics():
    rows = [row("a","S0",True,cost=2), row("b","S0",False,cost=1,human=1)]
    stats = condition_stats(rows)
    assert stats["vsr_pct"] == 50.0
    assert stats["fcr_declared_pct"] == 50.0
    assert stats["har_pct"] == 50.0
    assert stats["mcvo_usd"] == 3.0


def test_exact_mcnemar_counts_discordance():
    rows = []
    for i in range(6):
        base = row(f"a{i}","S0",False)
        base["workload_id"] = f"w{i}"
        cand = row(f"b{i}","S3",i < 4)
        cand["workload_id"] = f"w{i}"
        rows += [base, cand]
    pairs = pair_conditions(rows, "S0", "S3")
    out = mcnemar_exact(pairs, lambda r: r["outcome"]["verified_success"])
    assert out["n_pairs"] == 6
    assert out["c_right_only"] == 4
    assert 0 <= out["exact_p_two_sided"] <= 1


def test_paired_continuous_is_deterministic():
    rows = []
    for i in range(5):
        a = row(f"a{i}","S0",True,ttv=100+i)
        b = row(f"b{i}","S3",True,ttv=80+i)
        a["workload_id"] = b["workload_id"] = f"w{i}"
        rows += [a,b]
    pairs = pair_conditions(rows,"S0","S3")
    x = paired_continuous(pairs, lambda r: r["performance"]["time_to_verified_ms"], seed=1, bootstrap_samples=100)
    y = paired_continuous(pairs, lambda r: r["performance"]["time_to_verified_ms"], seed=1, bootstrap_samples=100)
    assert x == y
    assert x["mean_difference"] == -20.0


def test_confirmatory_mode_rejects_dry_run():
    try:
        analyze([row("a","S0",False)])
    except ValueError as exc:
        assert "non-LIVE_VALID" in str(exc)
    else:
        raise AssertionError("dry run must not enter confirmatory analysis")


def test_dry_run_mode_accepts_fixture():
    result = analyze([row("a","S0",False)], allow_dry_run=True)
    assert result["mode"] == "DRY_RUN_ALLOWED"
