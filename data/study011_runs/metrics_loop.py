#!/usr/bin/env python3
"""Loop: regenerate metrics + dashboard every 30s, detached."""
import subprocess, sys, time
GEN_DASH = str(Path(r"C:\Users\empir\Downloads\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026\data\study011_runs\generate_dashboard.py"))
GEN_METRICS = str(Path(r"C:\Users\empir\Downloads\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026\data\study011_runs\generate_metrics.py"))
while True:
    try:
        subprocess.run([sys.executable, GEN_DASH], timeout=15, capture_output=True)
        subprocess.run([sys.executable, GEN_METRICS], timeout=15, capture_output=True)
    except Exception: pass
    time.sleep(30)
