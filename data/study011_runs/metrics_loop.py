#!/usr/bin/env python3
"""Loop: regenerate metrics + dashboard every 30s. NO subprocess — imports directly."""
import sys, time, os
sys.path.insert(0, r"C:\Users\empir\Downloads\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026\data\study011_runs")
sys.path.insert(0, r"C:\Users\empir\Downloads\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026")

while True:
    try:
        # Import and run the generators directly (no subprocess = no console window)
        import generate_metrics
        generate_metrics.main()
        import generate_dashboard
        generate_dashboard.main()
    except Exception as e:
        print(f"loop error: {e}", file=__import__('sys').stderr)
    time.sleep(30)
