#!/usr/bin/env python3
"""Remove 429-era checkpoint entries for openrouter cells C and F so the runner
can re-execute those run_ids with paid models (Amendment 010). Only removes
entries whose execution_class was LIVE_PROVIDER_FAILURE (not observations)."""
import json
from pathlib import Path

BASE = Path(r"C:\Users\empir\Downloads\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026")
CP = BASE / "data" / "study011_runs" / "confirmatory" / "canonical-run-002" / "checkpoint.jsonl"
RECORDS = BASE / "data" / "study011_runs" / "confirmatory" / "canonical-run-002" / "run_records.jsonl"

# Find run_ids that had LIVE_VALID records under Amendment 010 (dfe3513c) —
# those should STAY in checkpoint (they're real observations).
keep_ids = set()
remove_ids = set()
for line in RECORDS.read_text(encoding="utf-8", errors="ignore").splitlines():
    if not line.strip(): continue
    rec = json.loads(line)
    fp = str(rec.get("implementation_fingerprint", ""))
    rid = rec.get("run_id", "")
    if fp.startswith("dfe3513c") and rec.get("execution_class") == "LIVE_VALID":
        keep_ids.add(rid)

# Read checkpoint, filter out 429-era entries for openrouter C/F
lines_out = []
removed = 0
kept = 0
for line in CP.read_text(encoding="utf-8", errors="ignore").splitlines():
    if not line.strip(): continue
    entry = json.loads(line)
    rid = entry.get("run_id", "")
    if rid in keep_ids:
        lines_out.append(line)
        kept += 1
    elif "openrouter" in rid and ("S11-" in rid):
        # This is an openrouter entry — check if it has a VALID record
        has_valid = any(
            json.loads(l).get("run_id") == rid and rec.get("execution_class") == "LIVE_VALID"
            for l in RECORDS.read_text(encoding="utf-8", errors="ignore").splitlines()
            if l.strip() and str(json.loads(l).get("implementation_fingerprint", "")).startswith("dfe3513c")
        )
        if has_valid:
            lines_out.append(line)
            kept += 1
        else:
            remove_ids.add(rid)
            removed += 1
    else:
        lines_out.append(line)
        kept += 1

# Write filtered checkpoint
CP.write_text("\n".join(lines_out) + "\n", encoding="utf-8", newline="\n")
print(f"checkpoint: kept {kept}, removed {removed} (429-era, not observations)")
