"""Tests for STUDY-011 pre-data analysis pipeline (offline, stdlib only).

Synthetic raw runs only. No network, no API keys, no live execution.
Covers: pairing, McNemar, replication codes (H1/H2/H3), LIVE_ONLY
rejection, economics, classification, and CLI outputs.
"""
import json
import os
import sys
import tempfile

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from experiments.live_benchmark import study011_analyze as s11


# ── Synthetic record factory ────────────────────────────────────────────────
def make_run(run_id, provider="dialagram", model="deepseek-v4", workload="SWE-01",
             replicate="1", condition="A", fcr=False, vsr=False, declared=True,
             actual=True, cost=0.01, latency=1200.0, prompt_tok=500, comp_tok=300,
             seed=None, **overrides):
    rec = {
        "run_id": run_id,
        "study_id": "STUDY-011",
        "provider_name": provider,
        "exact_model_id": model,
        "workload_id": workload,
        "replicate_id": replicate,
        "condition": condition,
        "is_live": True,
        "http_status": 200,
        "provider_request_id": f"req-{run_id}",
        "request_hash": "a" * 64,
        "response_hash": "b" * 64,
        "token_count_prompt": prompt_tok,
        "token_count_completion": comp_tok,
        "latency_ms": latency,
        "cost_usd": cost,
        "mission_state_final": "VERIFIED" if (vsr or declared) else "FAILED",
        "fcr_flag": fcr,
        "vsr_flag": vsr,
        "actual_success": actual,
        "declared_complete": declared,
        "control_plane_cost": 0.0001 if condition == "G" else 0.0,
        "verification_cost": 0.0002 if condition in ("F", "G") else 0.0,
        "raw_response": "task complete with required output alpha beta",
    }
    if seed is not None:
        rec["randomization_seed"] = seed
    rec.update(overrides)
    return rec


def test_wilson_cohens_mcnemar_match_study008_formulas():
    lo, hi = s11.wilson_ci(58, 100)
    assert 0.0 <= lo < 58.0 < hi <= 100.0
    assert s11.wilson_ci(0, 0) == (0.0, 0.0)
    assert s11.cohens_h(0.5, 0.5) == 0.0
    h = s11.cohens_h(0.1, 0.5)
    assert h > 0.5  # large gap exceeds SEOI
    chi2, p = s11.mcnemar_test(0, 0)
    assert (chi2, p) == (0.0, 1.0)
    chi2, p = s11.mcnemar_test(10, 2)
    # (|10-2|-1)^2/12 = 49/12 = 4.083
    assert chi2 == 4.083
    assert 0.03 < p < 0.06


def test_pairing_key_deterministic_and_replicate_parsing():
    r1 = make_run("study011-dialagram-A-SWE-01-r001", replicate="1")
    # explicit replicate wins over run_id suffix
    assert s11.pairing_key(r1) == ("dialagram", "deepseek-v4", "SWE-01", "1")
    r2 = {"run_id": "study011-openrouter-G-SWE-02-r007", "provider_name": "OpenRouter",
          "exact_model_id": "m1", "workload_id": "SWE-02", "condition": "G"}
    assert s11.pairing_key(r2) == ("openrouter", "m1", "SWE-02", "7")
    r3 = {"run_id": "bare-id", "provider_name": "dialagram",
          "exact_model_id": "m", "workload_id": "W", "condition": "A"}
    assert s11.replicate_of(r3) == "0"


def test_paired_dataset_rejects_unpaired_and_preserves_seed():
    runs = [
        make_run("a1", provider="dialagram", workload="SWE-01", replicate="1",
                 condition="A", seed="s-1"),
        make_run("g1", provider="dialagram", workload="SWE-01", replicate="1",
                 condition="G", seed="s-1"),
        make_run("a2", provider="dialagram", workload="SWE-02", replicate="1",
                 condition="A", seed="s-2"),
        # no G counterpart for SWE-02 -> unpaired
        make_run("a3", provider="dialagram", workload="SWE-03", replicate="1",
                 condition="A", seed="sx"),
        make_run("g3", provider="dialagram", workload="SWE-03", replicate="1",
                 condition="G", seed="sy-different"),
    ]
    norms = [s11.normalize_record(r, "LIVE_VALID") for r in runs]
    paired = s11.build_paired_dataset(norms, "A", "G")
    assert paired["n_pairs"] == 1
    assert paired["pairs"][0]["key"] == "dialagram|deepseek-v4|SWE-01|1"
    assert len(paired["unpaired_x"]) == 1  # SWE-02 A without G
    assert paired["seed_mismatches"] == ["dialagram|deepseek-v4|SWE-03|1"]


def test_mcnemar_from_pairs_counts_discordants():
    def pair(x_flag, y_flag):
        return {"key": "k", "x": {"fcr_flag": x_flag}, "y": {"fcr_flag": y_flag}}
    pairs = [pair(True, False)] * 6 + [pair(False, True)] * 2 + \
        [pair(True, True)] + [pair(False, False)] * 3
    out = s11.mcnemar_from_pairs(pairs, "fcr_flag")
    assert out["b_x_only"] == 6
    assert out["c_y_only"] == 2
    assert out["discordant"] == 8
    assert out["low_discordant"] is True  # 8 < 10 flags audit caution
    assert out["chi2"] == round(((6 - 2 - 1) ** 2) / 8, 3)


def test_live_only_rejects_simulation_and_nonlive():
    sim = make_run("sim1", condition="A",
                   raw_response="hello [Dialagram Sim: fallback]")
    try:
        s11.validate_integrity([sim])
    except s11.IntegrityError:
        pass
    else:
        raise AssertionError("simulation marker must raise IntegrityError")
    nonlive = make_run("nl1", condition="G", is_live=False)
    try:
        s11.validate_integrity([nonlive])
    except s11.IntegrityError:
        pass
    else:
        raise AssertionError("is_live=False in confirmatory set must raise")
    dup = [make_run("same-id", condition="A"), make_run("same-id", condition="G")]
    try:
        s11.validate_integrity(dup)
    except s11.IntegrityError:
        pass
    else:
        raise AssertionError("duplicate run_id must raise")
    dup_pair = [make_run("r1", workload="SWE-01", replicate="1", condition="A"),
                make_run("r2", workload="SWE-01", replicate="1", condition="A")]
    try:
        s11.validate_integrity(dup_pair)
    except s11.IntegrityError:
        pass
    else:
        raise AssertionError("duplicate pairing key in same condition must raise")


def test_classification_taxonomy():
    good = make_run("ok1", condition="A")
    assert s11.classify_execution(good) == "LIVE_VALID"
    fail = make_run("pf1", condition="A", http_status=429,
                    provider_request_id=None)
    assert s11.classify_execution(fail) == "LIVE_PROVIDER_FAILURE"
    bad_prov = make_run("ip1", condition="G", provider_request_id=None)
    assert s11.classify_execution(bad_prov) == "INVALID_PROTOCOL"
    proto = make_run("lp1", condition="F", assurance_invoked=False)
    assert s11.classify_execution(proto) == "LIVE_PROTOCOL_FAILURE"
    expl = make_run("ex1", condition="B")
    assert s11.classify_execution(expl) == "EXCLUDED"
    excl = make_run("ex2", condition="A", execution_class="EXCLUDED")
    assert s11.classify_execution(excl) == "EXCLUDED"
    missing_w = make_run("mw1", condition="A", workload_id="")
    assert s11.classify_execution(missing_w) == "INVALID_PROTOCOL"


def test_economics_cpvo_tvo_tax():
    rows = [
        s11.normalize_record(make_run(f"e{i}", condition="G", vsr=True,
                                      cost=0.02, latency=1000.0,
                                      control_plane_cost=0.002), "LIVE_VALID")
        for i in range(4)
    ]
    stat = s11.compute_cell_stats(rows)
    assert stat["n"] == 4
    assert stat["cpvo_usd"] == round(0.08 / 4, 4)
    assert stat["mean_tvo_ms"] == 1000.0  # falls back to latency when verified
    assert stat["mean_control_plane_tax"] == round(0.002 / 0.02, 4)
    empty = s11.compute_cell_stats([])
    assert empty["n"] == 0 and empty["cpvo_usd"] is None
    novs = [s11.normalize_record(make_run("z1", condition="A", vsr=False,
                                          declared=False, actual=False),
                                 "LIVE_VALID")]
    stat2 = s11.compute_cell_stats(novs)
    assert stat2["cpvo_usd"] is None
    assert stat2["abstained_count"] == 1  # live but never declared


def test_replication_h1_codes():
    alpha, seoi = 0.00333, 0.5
    sup = {"stratum": "s", "n_pairs": 58, "direction_correct": True,
           "h": 0.8, "p_value": 0.001}
    weak = {"stratum": "w", "n_pairs": 58, "direction_correct": True,
            "h": 0.3, "p_value": 0.05}
    negl = {"stratum": "n", "n_pairs": 58, "direction_correct": True,
            "h": 0.1, "p_value": 0.5}
    rev = {"stratum": "r", "n_pairs": 20, "direction_correct": False,
           "h": 0.6, "p_value": 0.001}
    rev_small = {"stratum": "rs", "n_pairs": 3, "direction_correct": False,
                 "h": 0.6, "p_value": 0.001}
    assert s11.classify_replication_h1(
        [dict(sup, stratum="a"), dict(sup, stratum="b")], alpha, seoi)["code"] == "SUPPORTED"
    out = s11.classify_replication_h1([dict(sup, stratum="a"), weak], alpha, seoi)
    assert out["code"] == "PARTIALLY_SUPPORTED"
    out = s11.classify_replication_h1([negl, dict(negl, stratum="n2")], alpha, seoi)
    assert out["code"] == "FAILED_TO_REPLICATE"
    out = s11.classify_replication_h1([dict(sup, stratum="a"), rev], alpha, seoi)
    assert out["code"] == "REVERSED"
    out = s11.classify_replication_h1([dict(sup, stratum="a"), rev_small], alpha, seoi)
    assert out["code"] == "PARTIALLY_SUPPORTED"
    assert out["reversal_warnings_low_n"] == ["rs"]


def test_replication_h2_tradeoff_gate():
    alpha, seoi = 0.00333, 0.5
    s_a = {"stratum": "a", "n_pairs": 58, "direction_correct": True,
           "h": 0.9, "p_value": 0.001}
    s_b = {"stratum": "b", "n_pairs": 58, "direction_correct": True,
           "h": 0.9, "p_value": 0.001}
    ok_trade = {"a": 0.5, "b": 1.0}  # pp inflation within 2pp tolerance
    out = s11.classify_replication_h2([s_a, s_b], ok_trade, alpha, seoi)
    assert out["code"] == "SUPPORTED"
    bad_trade = {"a": 5.0, "b": 1.0}  # stratum a inflates FCR by 5pp
    out = s11.classify_replication_h2([s_a, s_b], bad_trade, alpha, seoi)
    assert out["code"] == "PARTIALLY_SUPPORTED"
    assert out["tradeoff_demoted_strata"] == ["a"]
    rev = {"stratum": "r", "n_pairs": 30, "direction_correct": False,
           "h": 0.4, "p_value": 0.01}
    out = s11.classify_replication_h2([s_a, rev], None, alpha, seoi)
    assert out["code"] == "REVERSED"


def test_replication_h3_joint_gate():
    def gate(stratum, ok=True, reversed_dir=False, cpvo_g=0.01):
        return {"stratum": stratum, "n_pairs": 10,
                "fcr_a": 20.0, "fcr_g": 2.0 if ok else 8.0,
                "cpvo_a": 0.01, "cpvo_g": cpvo_g,
                "direction_correct": not reversed_dir}
    out = s11.classify_replication_h3([gate("a"), gate("b")])
    assert out["code"] == "SUPPORTED"
    out = s11.classify_replication_h3([gate("a"), gate("b", ok=False)])
    assert out["code"] == "PARTIALLY_SUPPORTED"
    out = s11.classify_replication_h3([gate("a", ok=False), gate("b", ok=False)])
    assert out["code"] == "FAILED_TO_REPLICATE"
    out = s11.classify_replication_h3([gate("a"), gate("r", reversed_dir=True)])
    assert out["code"] == "REVERSED"
    # cost blowout: CPVO(G) > 2x CPVO(A) fails the joint gate
    out = s11.classify_replication_h3([gate("a"), gate("b", cpvo_g=0.05)])
    assert out["code"] == "PARTIALLY_SUPPORTED"
    # null CPVO cannot pass
    null_gate = {"stratum": "z", "n_pairs": 10, "fcr_a": 20.0, "fcr_g": 1.0,
                 "cpvo_a": 0.01, "cpvo_g": None, "direction_correct": True}
    out = s11.classify_replication_h3([gate("a"), null_gate])
    assert out["code"] == "PARTIALLY_SUPPORTED"


def _write_input_dir(tmpdir, records):
    in_dir = os.path.join(tmpdir, "in")
    os.makedirs(in_dir, exist_ok=True)
    path = os.path.join(in_dir, "runs.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    return in_dir


def test_cli_writes_three_artifacts_and_reports_replication():
    records = []
    rid = 0
    for provider in ("dialagram", "openrouter"):
        for workload in ("SWE-01", "SWE-02"):
            for rep in ("1", "2"):
                rid += 1
                # A: false-completes; G: verifies (H1 direction correct)
                records.append(make_run(f"r{rid}a-{provider}-{workload}-{rep}",
                                        provider=provider, workload=workload,
                                        replicate=rep, condition="A",
                                        fcr=True, vsr=False, declared=True,
                                        actual=False, cost=0.01))
                rid += 1
                records.append(make_run(f"r{rid}g-{provider}-{workload}-{rep}",
                                        provider=provider, workload=workload,
                                        replicate=rep, condition="G",
                                        fcr=False, vsr=True, declared=True,
                                        actual=True, cost=0.015))
                rid += 1
                # C: fails; F: recovers (H2 direction correct)
                records.append(make_run(f"r{rid}c-{provider}-{workload}-{rep}",
                                        provider=provider, workload=workload,
                                        replicate=rep, condition="C",
                                        fcr=False, vsr=False, declared=False,
                                        actual=False, cost=0.01))
                rid += 1
                records.append(make_run(f"r{rid}f-{provider}-{workload}-{rep}",
                                        provider=provider, workload=workload,
                                        replicate=rep, condition="F",
                                        fcr=False, vsr=True, declared=True,
                                        actual=True, cost=0.012))
    with tempfile.TemporaryDirectory() as tmpdir:
        in_dir = _write_input_dir(tmpdir, records)
        out_dir = os.path.join(tmpdir, "out")
        rc = s11.main(["--input-dir", in_dir, "--output-dir", out_dir,
                       "--alpha-adj", "0.00333", "--seoi-h", "0.5"])
        assert rc == 0
        for fname in ("summary.md", "results.json", "tables.csv"):
            assert os.path.exists(os.path.join(out_dir, fname)), fname
        with open(os.path.join(out_dir, "results.json"), encoding="utf-8") as fh:
            results = json.load(fh)
        assert results["attempt_accounting"]["attempted_total"] == len(records)
        assert results["attempt_accounting"]["live_valid_total"] == len(records)
        assert set(results["replication"]) == {"H1", "H2", "H3"}
        for hyp in ("H1", "H2", "H3"):
            assert results["replication"][hyp]["code"] in s11.REPLICATION_CODES
        # Primary metrics + economics present per cell
        cell = results["cells"]["dialagram|A"]
        for key in ("vsr", "fcr_reported", "actual_success_rate",
                    "abstention_rate", "recovery_rate", "constraint_retention_rate",
                    "unauthorized_action_rate", "total_cost_usd", "cpvo_usd",
                    "mean_latency_ms", "mean_tokens", "mean_tvo_ms",
                    "mean_control_plane_tax"):
            assert key in cell, key


def test_cli_exits_nonzero_on_integrity_violation():
    bad = [make_run("bad1", condition="A",
                    raw_response="x [Dialagram Sim: fallback]")]
    with tempfile.TemporaryDirectory() as tmpdir:
        in_dir = _write_input_dir(tmpdir, bad)
        out_dir = os.path.join(tmpdir, "out")
        rc = s11.main(["--input-dir", in_dir, "--output-dir", out_dir])
        assert rc == 2
        assert not os.path.exists(os.path.join(out_dir, "results.json"))
