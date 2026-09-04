#!/usr/bin/env python3
"""Wrapper script for STUDY-011 that loads .study011_env before running harness."""

import os
import sys
from pathlib import Path

# Get base directory
base = Path(__file__).parent
os.chdir(base)

# Load .study011_env into os.environ
env_file = base / ".study011_env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()
    print(f"Loaded API keys from {env_file}", file=sys.stderr)

# Add experiments/live_benchmark to path for imports
sys.path.insert(0, str(base / "experiments" / "live_benchmark"))

# Run the harness
from run_study_011 import main
main()
