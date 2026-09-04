#!/usr/bin/env python3
"""Generate study011-metrics.json for the live dashboard. Run every 30s via Task Scheduler."""
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
BASE = Path(r"C:\Users\empir\Downloads\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026")
OUT = BASE / "docs" / "study011-metrics.json"
RUNS = BASE / "data" / "study011_runs" / "confirmatory" / "canonical-run-002"
def main():
    recs = []
    rf = RUNS / "run_records.jsonl"
    if rf.exists():
        for line in rf.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip():
                try: recs.append(json.loads(line))
                except: pass
    cells = {}
    for x in recs:
        k = f"{x.get('provider_name','?')}|{x.get('condition','?')}"
        c = cells.setdefault(k, {"att":0,"lv":0,"fail":0})
        c["att"] += 1
        if x.get("execution_class")=="LIVE_VALID": c["lv"] += 1
        else: c["fail"] += 1
    a010 = [x for x in recs if str(x.get("implementation_fingerprint","")).startswith("dfe3513c")]
    a010_cells = {}
    for x in a010:
        k = f"{x.get('provider_name','?')}|{x.get('condition','?')}"
        c = a010_cells.setdefault(k, {"att":0,"lv":0})
        c["att"] += 1
        if x.get("execution_class")=="LIVE_VALID": c["lv"] += 1
    blocks = {
        "original_confirmatory": {"fp": "b6b7c2d0…", "records": sum(1 for x in recs if str(x.get("implementation_fingerprint","")).startswith("b6b7c2d0"))},
        "original_openrouter_free": {"fp": "0c588022…", "records": sum(1 for x in recs if x.get("provider_name")=="openrouter" and str(x.get("implementation_fingerprint","")).startswith("0c588022"))},
        "post_amendment_010": {"fp": "dfe3513c…", "records": len(a010)},
    }
    data = {
        "cells": cells,
        "a010_cells": a010_cells,
        "total_records": len(recs),
        "total_valid": sum(1 for x in recs if x.get("execution_class")=="LIVE_VALID"),
        "a010_records": len(a010),
        "a010_valid": sum(1 for x in a010 if x.get("execution_class")=="LIVE_VALID"),
        "blocks": blocks,
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1), encoding="utf-8", newline="\n")
    print(f"metrics updated: {len(recs)} records, {data['total_valid']} valid")
if __name__ == "__main__":
    main()
