#!/usr/bin/env python3
"""
STUDY-011 Single-Instance Runner with Lock File.
Uses a lock file to ensure only ONE instance runs at a time.
No loop wrapper, no watchdog — just the runner + a health-check API endpoint.
"""
import subprocess, sys, os, time, json
from pathlib import Path

BASE = Path(r"C:\Users\empir\Downloads\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026")
LOCK_FILE = BASE / "data" / "study011_runs" / "confirmatory" / "canonical-run-002" / "RUNNER.lock"
LOG = BASE / "data" / "study011_runs" / "confirmatory" / "canonical-run-002" / "console.log"
CREATE_NO_WINDOW = 0x08000000
DETACHED = 0x00000008 | 0x00000200

def load_key(paths, name):
    for p in paths:
        pp = Path(p)
        if not pp.exists(): continue
        for line in pp.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if s.startswith(f"{name}=") and not s.startswith("#"):
                return s.split("=", 1)[1].strip().strip('"').strip("'")
    return None

def acquire_lock():
    """Try to acquire the lock file. Returns True if acquired."""
    try:
        # O_CREAT | O_EXCL — fails if file already exists
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False

def release_lock():
    LOCK_FILE.unlink(missing_ok=True)

def count_cells_done():
    """Count cells with >= 58 LIVE_VALID records."""
    records_file = BASE / "data" / "study011_runs" / "confirmatory" / "canonical-run-002" / "run_records.jsonl"
    if not records_file.exists(): return 0
    from collections import Counter
    cells = {}
    for line in records_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip(): continue
        try:
            rec = json.loads(line)
            if rec.get("execution_class") != "LIVE_VALID": continue
            key = f"{rec.get('provider_name','?')}|{rec.get('condition','?')}"
            cells[key] = cells.get(key, 0) + 1
        except: pass
    return sum(1 for v in cells.values() if v >= 58)

def main():
    if not acquire_lock():
        print("Another instance is already running. Exiting.")
        sys.exit(1)
    
    print(f"[{time.strftime('%H:%M:%S')}] Lock acquired. Starting runner.")
    
    env = dict(os.environ)
    env["OPENROUTER_API_KEY"] = load_key([
        Path.home()/"AppData/Local/hermes/.env",
        Path.home()/"AppData/Local/hermes/profiles/avc/.env"
    ], "OPENROUTER_API_KEY")
    env["DIALAGRAM_API_KEY"] = load_key([
        Path.home()/"AppData/Local/hermes/profiles/avc/.env"
    ], "HERMES_CUSTOM_DIALAGRAM_ME_API_KEY")
    
    max_restarts = 30
    for attempt in range(max_restarts):
        if count_cells_done() >= 8:
            print("ALL 8 CELLS COMPLETE — exiting.")
            break
        
        with open(LOG, "a", encoding="utf-8", newline="\n") as lh:
            lh.write(f"\n=== SINGLE-INSTANCE RUNNER iteration {attempt+1} ===\n")
            lh.flush()
            proc = subprocess.Popen(
                [r"C:\Users\empir\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none\pythonw.exe", "experiments/live_benchmark/run_study_011.py",
                 "--mode", "LIVE_ONLY", "--phase", "1",
                 "--workload-file", str(BASE / "data/study011_workload_manifest.json"),
                 "--output-dir", str(BASE / "data/study011_runs/confirmatory/canonical-run-002")],
                stdout=lh, stderr=subprocess.STDOUT, cwd=str(BASE), env=env,
                creationflags=CREATE_NO_WINDOW
            )
            print(f"[{time.strftime('%H:%M:%S')}] iteration {attempt+1} PID {proc.pid}")
        
        proc.wait()
        
        # Check completion
        cells_done = count_cells_done()
        print(f"[{time.strftime('%H:%M:%S')}] exited code={proc.returncode} | cells done: {cells_done}/8")
        
        if cells_done >= 8:
            print("ALL 8 CELLS COMPLETE — study done!")
            break
        
        if proc.returncode == 0:
            print("Clean exit — checking if complete...")
            continue
        
        time.sleep(10)  # cooldown before restart
    
    # Release lock
    LOCK_FILE.unlink(missing_ok=True)
    print(f"[{time.strftime('%H:%M:%S')}] Lock released. Done.")

if __name__ == "__main__":
    main()
