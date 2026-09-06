from __future__ import annotations


def decide_runtime(*, promoted: bool, doctor_ok: bool, hashes_ok: bool, disabled: bool) -> dict[str, object]:
    if disabled:
        return {"runtime": "stock", "fallback": True, "reason": "kill_switch"}
    if not promoted:
        return {"runtime": "stock", "fallback": True, "reason": "not_promoted"}
    if not hashes_ok:
        return {"runtime": "stock", "fallback": True, "reason": "integrity_mismatch"}
    if not doctor_ok:
        return {"runtime": "stock", "fallback": True, "reason": "doctor_failed"}
    return {"runtime": "toolrush", "fallback": False, "reason": "promoted_healthy"}


def toolrush_env() -> dict[str, str]:
    return {
        "TOOLRUSH_FASTLANE": "1",
        "TOOLRUSH_SEARCH": "1",
        "TOOLRUSH_PERSIST": "1",
    }
