from __future__ import annotations


def check_preflight(snapshot: dict, limits: dict) -> dict:
    """Classify whether a host snapshot is clean enough for confirmatory timing."""
    reasons = []
    if float(snapshot.get("cpu_percent", 100.0)) > float(limits["cpu_percent_max"]):
        reasons.append("cpu_percent")
    if float(snapshot.get("memory_percent", 100.0)) > float(limits["memory_percent_max"]):
        reasons.append("memory_percent")
    if limits.get("require_ac_power") is True and snapshot.get("on_ac_power") is not True:
        reasons.append("on_ac_power")
    return {"clean": not reasons, "reasons": reasons}
