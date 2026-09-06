from pathlib import Path

import yaml

EXPECTED_EXPERIMENT_ID = "JAR-EXP-0013"


def load_protocol(path: Path) -> dict:
    """Load and minimally validate the frozen experiment protocol."""
    protocol_path = Path(path)
    with protocol_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("protocol must be a mapping")
    if data.get("experiment_id") != EXPECTED_EXPERIMENT_ID:
        raise ValueError("unexpected experiment_id")
    return data
