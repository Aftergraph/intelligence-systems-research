from __future__ import annotations

from datetime import datetime, timezone
import os
import platform
import sys


def capture_environment() -> dict:
    """Capture non-secret host metadata required for reproducibility."""
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "cpu_logical_count": os.cpu_count() or 1,
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "executable": sys.executable,
    }
