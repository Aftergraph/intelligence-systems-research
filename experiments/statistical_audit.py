import csv
import hashlib
import json
import math
import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

# ponytail: Wilson Score Interval computation for rigorous sample-bounded proportions.
# Replaces ungrounded claims of "elimination" with exact confidence bounds.

def wilson_score_interval(successes, total, confidence=0.95):
    """
    Computes Wilson score interval for a binomial proportion.
    """
    if total == 0:
        return (0.0, 0.0)
    z = 1.95996  # 95% confidence
    p = successes / total
    denom = 1 + (z**2 / total)
    centre = (p + (z**2 / (2 * total))) / denom
    spread = (z * math.sqrt((p * (1 - p) / total) + (z**2 / (4 * total**2)))) / denom
    lower = max(0.0, centre - spread)
    upper = min(1.0, centre + spread)
    return (round(lower * 100, 2), round(upper * 100, 2))

def cohens_h(p1, p2):
    """
    Computes Cohen's h effect size between two proportions.
    h = 2 * arcsin(sqrt(p1)) - 2 * arcsin(sqrt(p2))
    """
    phi1 = 2 * math.asin(math.sqrt(max(0.0, min(1.0, p1))))
    phi2 = 2 * math.asin(math.sqrt(max(0.0, min(1.0, p2))))
    return round(abs(phi1 - phi2), 3)

def audit_datasets():
    audit_records = []

    # 1. Audit JAR-EXP-0001 (data/results_jar_exp_0001.csv)
    jar_path = os.path.join(workspace, "data", "results_jar_exp_0001.csv")
    if os.path.exists(jar_path):
        with open(jar_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        conds = sorted(list(set(r["condition"] for r in rows)))
        for c in conds:
            sub = [r for r in rows if r["condition"] == c]
            n = len(sub)
            v_succ = sum(1 for r in sub if r["is_verified"].lower() == "true")
            decl = sum(1 for r in sub if r["declared_success"].lower() == "true")
            fc = sum(1 for r in sub if r["is_false_completion"].lower() == "true")

            vsr_pct = round(v_succ / n * 100, 1)
            vsr_ci = wilson_score_interval(v_succ, n)
            
            fcr_pct = round((fc / decl * 100), 1) if decl > 0 else 0.0
            fcr_ci = wilson_score_interval(fc, decl) if decl > 0 else (0.0, 0.0)

            audit_records.append({
                "dataset": "JAR-EXP-0001 (SWE Workloads, N=50)",
                "condition": c,
                "sample_size": n,
                "declared_successes": decl,
                "actual_verified": v_succ,
                "false_completions": fc,
                "VSR_pct": vsr_pct,
                "VSR_95_CI": f"[{vsr_ci[0]}%, {vsr_ci[1]}%]",
                "FCR_pct": fcr_pct,
                "FCR_95_CI": f"[{fcr_ci[0]}%, {fcr_ci[1]}%]"
            })

    # 2. Audit MISSION-Bench (data/results_mission_bench.csv)
    mb_path = os.path.join(workspace, "data", "results_mission_bench.csv")
    if os.path.exists(mb_path):
        with open(mb_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        stages = sorted(list(set(r["ablation_stage"] for r in rows)))
        for st in stages:
            sub = [r for r in rows if r["ablation_stage"] == st]
            n = len(sub)
            v_succ = sum(1 for r in sub if r["is_verified"].lower() == "true")
            decl = sum(1 for r in sub if r["declared_success"].lower() == "true")
            fc = sum(1 for r in sub if r["is_false_completion"].lower() == "true")

            vsr_pct = round(v_succ / n * 100, 1)
            vsr_ci = wilson_score_interval(v_succ, n)
            
            fcr_pct = round((fc / decl * 100), 1) if decl > 0 else 0.0
            fcr_ci = wilson_score_interval(fc, decl) if decl > 0 else (0.0, 0.0)

            audit_records.append({
                "dataset": "MISSION-Bench (Multi-Domain, N=100)",
                "condition": st,
                "sample_size": n,
                "declared_successes": decl,
                "actual_verified": v_succ,
                "false_completions": fc,
                "VSR_pct": vsr_pct,
                "VSR_95_CI": f"[{vsr_ci[0]}%, {vsr_ci[1]}%]",
                "FCR_pct": fcr_pct,
                "FCR_95_CI": f"[{fcr_ci[0]}%, {fcr_ci[1]}%]"
            })

    # 3. Audit Confounder Analysis (data/results_confounder_analysis.csv)
    conf_path = os.path.join(workspace, "data", "results_confounder_analysis.csv")
    if os.path.exists(conf_path):
        with open(conf_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        c_names = sorted(list(set(r["condition"] for r in rows)))
        for cn in c_names:
            sub = [r for r in rows if r["condition"] == cn]
            n = len(sub)
            v_succ = sum(1 for r in sub if r["is_verified"].lower() == "true")
            decl = sum(1 for r in sub if r["declared_success"].lower() == "true")
            fc = sum(1 for r in sub if r["is_false_completion"].lower() == "true")

            vsr_pct = round(v_succ / n * 100, 1)
            vsr_ci = wilson_score_interval(v_succ, n)
            
            fcr_pct = round((fc / decl * 100), 1) if decl > 0 else 0.0
            fcr_ci = wilson_score_interval(fc, decl) if decl > 0 else (0.0, 0.0)

            audit_records.append({
                "dataset": "Confounder Analysis (N=100)",
                "condition": cn,
                "sample_size": n,
                "declared_successes": decl,
                "actual_verified": v_succ,
                "false_completions": fc,
                "VSR_pct": vsr_pct,
                "VSR_95_CI": f"[{vsr_ci[0]}%, {vsr_ci[1]}%]",
                "FCR_pct": fcr_pct,
                "FCR_95_CI": f"[{fcr_ci[0]}%, {fcr_ci[1]}%]"
            })

    out_csv = os.path.join(workspace, "data", "statistical_audit_recomputed.csv")
    import io as _io
    csv_buf = _io.StringIO()
    writer = csv.DictWriter(csv_buf, fieldnames=list(audit_records[0].keys()))
    writer.writeheader()
    writer.writerows(audit_records)
    with open(out_csv, "wb") as f:
        f.write(csv_buf.getvalue().replace("\r\n", "\n").encode("utf-8"))

    print(f"Recomputed statistical audit written to: {out_csv}")
    return audit_records

if __name__ == "__main__":
    records = audit_datasets()
    for r in records:
        print(f"{r['dataset']} | {r['condition']}: VSR={r['VSR_pct']}% {r['VSR_95_CI']} | FCR={r['FCR_pct']}% {r['FCR_95_CI']}")
