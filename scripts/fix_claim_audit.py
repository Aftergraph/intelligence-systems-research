"""Fix claim_evidence_audit.csv: reclassify live benchmark and router evaluation rows."""
import csv, io, sys

csv_path = "data/claim_evidence_audit.csv"

with open(csv_path, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

changes = 0
for row in rows:
    claim = row["CLAIM"]

    # Row: live benchmark claim
    if "eliminates false completions under live stochastic" in claim:
        row["CLAIM"] = (
            "No false completions observed in the LIVE_VALID sample under evidence gating "
            "(2 LIVE_VALID / 9 LIVE_PROVIDER_FAILURE / 264 SIMULATED from 275 attempted runs)"
        )
        row["EVIDENCE TYPE"] = "Live Multi-Model Benchmark (Partial)"
        row["SOURCE"] = (
            "experiments/live_benchmark/run_study_008.py; "
            "experiments/live_benchmark/normalize_and_analyze.py"
        )
        row["SAMPLE SIZE"] = "275 attempted; 2 LIVE_VALID, 9 LIVE_PROVIDER_FAILURE, 264 SIMULATED"
        row["STATISTICAL RESULT"] = (
            "Simulated conditions: McNemar chi2=40.024, p<0.000001, Cohen's h=1.671 (A vs G FCR); "
            "LIVE_VALID cell: N=2, FCR=0.0%, 95% Wilson CI [0.0%, 79.3%] — insufficient for inference"
        )
        row["CONFIDENCE INTERVAL"] = "LIVE_VALID 95% Wilson CI: [0.0%, 79.3%] (N=2, non-inferential)"
        row["SIMULATED OR LIVE?"] = (
            "PARTIAL — 2/275 LIVE_VALID; 264 SIMULATED due to harness bug (is_live_call = idx==0)"
        )
        row["LIMITATIONS"] = (
            "Harness bug caused 264/275 runs to use offline simulation. "
            "9 LIVE_PROVIDER_FAILURE due to rate limiting on SWE-01 full prompt. "
            "Only 2 confirmed live model calls. "
            "Router evaluation separately classified SIMULATION_SUPPORTED."
        )
        row["STATUS"] = "PARTIAL_LIVE_SUPPORTED"
        changes += 1
        print("  [FIXED] Live benchmark row")

    # Row: router evaluation claim
    elif "Policy-constrained scored routing matches frontier" in claim:
        row["CLAIM"] = (
            "Policy-constrained scored routing matches frontier model performance at lower cost "
            "in simulated routing benchmark"
        )
        row["EVIDENCE TYPE"] = "Routing Simulation Study"
        row["SIMULATED OR LIVE?"] = (
            "SIMULATED — router evaluation used simulated VSR/FCR outcomes; "
            "model catalog from Dialagram but behavioral outcomes computed by simulation harness"
        )
        row["LIMITATIONS"] = (
            "All routing outcomes simulated; not driven by live model task completion scoring"
        )
        row["STATUS"] = "SIMULATION_SUPPORTED"
        changes += 1
        print("  [FIXED] Router evaluation row")

print(f"\nTotal rows changed: {changes}")

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Written: {csv_path}")
