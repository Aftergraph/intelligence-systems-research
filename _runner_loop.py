#!/usr/bin/env python3
"""STUDY-011 resilient runner wrapper — auto-restarts on silent death."""
import subprocess, sys, os, time
from pathlib import Path

BASE = r"C:\Users\empir\Downloads\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026"
OUT_DIR = BASE / "data" / "study011_runs" / "confirmatory" / "canonical-run-002"
LOG = OUT_DIR / "console.log"
MAX_RUNS = 50  # safety limit

def load_key(paths, name):
    for p in paths:
        pp = Path(p)
        if not pp.exists(): continue
        for line in pp.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if s.startswith(f"{name}=") and not s.startswith("#"):
                return s.split("=", 1)[1].strip().strip('"').strip("'")
    return None

def main():
    env = dict(os.environ)
    env["OPENROUTER_API_KEY"] = load_key([
        Path.home()/"AppData/Local/hermes/.env",
        Path.home()/"AppData/Local/hermes/profiles/avc/.env"
    ], "OPENROUTER_API_KEY")
    env["DIALAGRAM_API_KEY"] = load_key([
        Path.home()/"AppData/Local/hermes/profiles/avc/.env"
    ], "HERMES_CUSTOM_DIALAGRAM_ME_API_KEY")
    
    for attempt in range(MAX_RUNS):
        with open(LOG, "a", encoding="utf-8", newline="\n") as lh:
            lh.write(f"\n=== RESUME LOOP iteration {attempt+1} ===\n")
            lh.flush()
            proc = subprocess.Popen(
                [sys.executable, "experiments/live_benchmark/run_study_011.py",
                 "--mode", "LIVE_ONLY", "--phase", "1",
                 "--workload-file", str(BASE / "data/study011_workload_manifest.json"),
                 "--output-dir", str(OUT_DIR)],
                stdout=lh, stderr=subprocess.STDOUT, cwd=BASE, env=env
            )
            print(f"[{time.strftime('%H:%M:%S')}] iteration {attempt+1} PID {proc.pid}")
        
        # Wait for exit
        proc.wait()
        exit_code = proc.returncode
        print(f"[{time.strftime('%H:%M:%S')}] exited code={exit_code}")
        
        # Check if study is complete (all 8 cells viable) — read console tail
        console = (OUT_DIR / "console.log").read_text(encoding="utf-8", errors="ignore")
        if console.count("viable=True") >= 8:
            print("ALL CELLS COMPLETE — stopping loop")
            break
        
        if exit_code == 0:
            print("clean exit — study likely complete")
            break
        
        time.sleep(5)  # brief pause between restarts

if __name__ == "__main__":
    main()
