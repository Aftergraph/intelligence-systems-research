from __future__ import annotations

from experiments.runtime_acceleration.adapters.browser_base import BrowserUnavailable, BrowserUnsupported
from experiments.runtime_acceleration.verification.differential import compare_observable


def run_browser_conformance(control, treatment, cases: list[dict]) -> dict:
    results = []
    passed = 0
    for case in cases:
        operation = case["operation"]
        payload = case.get("payload", {})
        try:
            control_observable = control.perform(operation, payload)
        except (BrowserUnavailable, BrowserUnsupported) as exc:
            results.append({"id": case.get("id"), "classification": "CONTROL_INVALID", "detail": str(exc)})
            continue
        try:
            treatment_observable = treatment.perform(operation, payload)
        except BrowserUnavailable as exc:
            results.append({"id": case.get("id"), "classification": "UNAVAILABLE", "detail": str(exc)})
            continue
        except BrowserUnsupported as exc:
            results.append({"id": case.get("id"), "classification": "UNSUPPORTED", "detail": str(exc)})
            continue
        diff = compare_observable(control_observable, treatment_observable)
        if diff.equal:
            passed += 1
        results.append({
            "id": case.get("id"),
            "classification": diff.classification,
            "control": control_observable,
            "treatment": treatment_observable,
            "details": diff.details,
        })
    return {"passed": passed, "total": len(cases), "cases": results}
