#!/usr/bin/env python3
"""Loop: generate metrics every 30s, detached."""
import subprocess, sys, time, os
GEN = str(Path(r"C:\Users\empir\Downloads\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026\data\study011_runs\generate_metrics.py"))
while True:
    try: subprocess.run([sys.executable, GEN], timeout=15, capture_output=True)
    except Exception: pass
    time.sleep(30)
