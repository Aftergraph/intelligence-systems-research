from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis.analyze import paired_bootstrap_median_reduction
from .protocol import load_protocol

_EXPECTED_CONDITIONS = ("A", "B")


def _require_mapping(value, label: str) -> dict:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a mapping")
    return value


def _metric(run: dict) -> float | None:
    metrics = run.get("metrics")
    if not isinstance(metrics, dict):
        return None
    value = metrics.get("tool_wall_clock_ms")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if value > 0.0 else None


def _verified(run: dict) -> bool:
    verifier = run.get("verifier")
    return isinstance(verifier, dict) and verifier.get("verified") is True


def _group_runs(summary: dict) -> tuple[dict[str, dict[str, dict]], list[str]]:
    runs = summary.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("Phase-2 summary has no completed runs")

    grouped: dict[str, dict[str, dict]] = {}
    duplicate_pairs: set[str] = set()
    for raw in runs:
        run = _require_mapping(raw, "run")
        pair_id = run.get("pair_id")
        condition = run.get("condition")
        if not isinstance(pair_id, str) or not pair_id:
            raise ValueError("every Phase-2 run requires a pair_id")
        if condition not in _EXPECTED_CONDITIONS:
            raise ValueError(f"invalid Phase-2 condition: {condition}")
        by_condition = grouped.setdefault(pair_id, {})
        if condition in by_condition:
            duplicate_pairs.add(pair_id)
        by_condition[condition] = run
    return grouped, sorted(duplicate_pairs)


def _effect(
    control: list[float],
    treatment: list[float],
    *,
    seed: int,
    resamples: int,
    paired_blocks: int,
) -> dict:
    value = paired_bootstrap_median_reduction(
        control,
        treatment,
        seed=seed,
        resamples=resamples,
    )
    value.update(
        {
            "status": "ESTIMATED",
            "metric": "tool_wall_clock_ms",
            "control_condition": "A",
            "treatment_condition": "B",
            "paired_blocks": paired_blocks,
            "confidence_level": 0.95,
        }
    )
    return value


def _inconclusive_effect(reason: str, paired_blocks: int) -> dict:
    return {
        "status": "INCONCLUSIVE",
        "reason": reason,
        "metric": "tool_wall_clock_ms",
        "control_condition": "A",
        "treatment_condition": "B",
        "paired_blocks": paired_blocks,
        "confidence_level": 0.95,
        "method": "paired_percentile_bootstrap",
    }


def analyze_phase2_summary(summary: dict, protocol: dict) -> dict:
    """Analyze authoritative Phase-2 A/B tool microbenchmarks without promoting G-TR.

    Warm samples are the confirmatory timing evidence. Cold samples are reported separately and
    never pooled into the warm effect. The overall effect pools equal-count paired warm blocks
    across the frozen operations, preserving A/B pair identity during bootstrap resampling.
    """
    summary = _require_mapping(summary, "summary")
    protocol = _require_mapping(protocol, "protocol")
    if (
        summary.get("experiment_id") != "JAR-EXP-0013"
        or protocol.get("experiment_id") != "JAR-EXP-0013"
    ):
        raise ValueError("unexpected JAR-EXP-0013 experiment identity")
    if summary.get("phase") != "TOOL_MICROBENCH":
        raise ValueError("Phase-2 analysis requires TOOL_MICROBENCH evidence")

    analysis = _require_mapping(protocol.get("analysis"), "protocol analysis")
    if analysis.get("effect_interval_method") != "paired_percentile_bootstrap":
        raise ValueError("Phase-2 analysis requires paired_percentile_bootstrap")
    if float(analysis.get("confidence_level", 0.0)) != 0.95:
        raise ValueError("Phase-2 analyzer is frozen to the preregistered 95% interval")
    seed = int(analysis["bootstrap_seed"])
    resamples = int(analysis["bootstrap_resamples"])
    if resamples < 1:
        raise ValueError("bootstrap_resamples must be >= 1")

    thresholds = _require_mapping(protocol.get("thresholds"), "protocol thresholds")
    required_reduction = float(thresholds["tool_overhead_reduction_min"])
    require_ci = bool(analysis.get("promotion_requires_ci_lower_bound", False))

    grouped, duplicates = _group_runs(summary)
    incomplete_pairs: list[str] = []
    invalid_metric_pairs: list[str] = []
    unverified_treatment_pairs: list[str] = []
    cold: dict[str, dict] = {}
    warm_by_operation: dict[str, list[tuple[str, float, float]]] = {}

    derived_correctness_failures = 0
    for pair_id, by_condition in grouped.items():
        if set(by_condition) != set(_EXPECTED_CONDITIONS):
            incomplete_pairs.append(pair_id)
            continue
        a = by_condition["A"]
        b = by_condition["B"]
        signature_a = (
            a.get("operation"),
            a.get("sample_kind"),
            a.get("repetition"),
        )
        signature_b = (
            b.get("operation"),
            b.get("sample_kind"),
            b.get("repetition"),
        )
        if signature_a != signature_b:
            incomplete_pairs.append(pair_id)
            continue
        operation, sample_kind, repetition = signature_a
        if not isinstance(operation, str) or not operation:
            incomplete_pairs.append(pair_id)
            continue
        if sample_kind not in {"cold", "warm"}:
            incomplete_pairs.append(pair_id)
            continue

        if not _verified(b):
            derived_correctness_failures += 1
            unverified_treatment_pairs.append(pair_id)

        a_metric = _metric(a)
        b_metric = _metric(b)
        if a_metric is None or b_metric is None:
            invalid_metric_pairs.append(pair_id)
            continue

        if sample_kind == "cold":
            cold[operation] = {
                "pair_id": pair_id,
                "repetition": repetition,
                "control_ms": a_metric,
                "treatment_ms": b_metric,
                "observed_reduction": (a_metric - b_metric) / a_metric,
                "verified": _verified(a) and _verified(b),
            }
        else:
            warm_by_operation.setdefault(operation, []).append(
                (pair_id, a_metric, b_metric)
            )

    declared_failures = int(
        summary.get("correctness_failures", derived_correctness_failures)
    )
    if declared_failures != derived_correctness_failures:
        raise ValueError(
            "Phase-2 correctness_failures does not match completed run verifier evidence"
        )

    operation_effects: dict[str, dict] = {}
    pooled_control: list[float] = []
    pooled_treatment: list[float] = []
    for operation in sorted(warm_by_operation):
        pairs = sorted(
            warm_by_operation[operation],
            key=lambda item: item[0],
        )
        control = [item[1] for item in pairs]
        treatment = [item[2] for item in pairs]
        pooled_control.extend(control)
        pooled_treatment.extend(treatment)
        operation_effects[operation] = _effect(
            control,
            treatment,
            seed=seed,
            resamples=resamples,
            paired_blocks=len(pairs),
        )

    if pooled_control and len(pooled_control) == len(pooled_treatment):
        overall = _effect(
            pooled_control,
            pooled_treatment,
            seed=seed,
            resamples=resamples,
            paired_blocks=len(pooled_control),
        )
    else:
        overall = _inconclusive_effect(
            "no_valid_paired_warm_evidence", len(pooled_control)
        )

    contaminated_pairs = int(summary.get("contaminated_pairs", 0))
    incomplete = bool(
        duplicates
        or incomplete_pairs
        or invalid_metric_pairs
        or contaminated_pairs
    )
    component_reasons: list[str] = []
    if declared_failures:
        component_verdict = "FAIL"
        component_reasons.append("correctness_failure")
    elif incomplete:
        component_verdict = "INCONCLUSIVE"
        component_reasons.append("incomplete_paired_warm_evidence")
    elif overall.get("status") != "ESTIMATED":
        component_verdict = "INCONCLUSIVE"
        component_reasons.append("tool_overhead_effect_unavailable")
    else:
        observed = float(overall["observed_reduction"])
        ci_low = float(overall["ci_low"])
        if observed < required_reduction:
            component_verdict = "FAIL"
            component_reasons.append("tool_overhead_reduction_below_threshold")
        elif require_ci and ci_low < required_reduction:
            component_verdict = "INCONCLUSIVE"
            component_reasons.append("tool_overhead_reduction_ci_below_threshold")
        else:
            component_verdict = "PASS"

    promotion_gates = {
        "G-TR": {
            "verdict": "INCONCLUSIVE",
            "reasons": [
                "phase2_tool_microbench_only",
                "tool_mission_wall_and_mission_success_evidence_required",
            ],
        },
        "G-OB": {"verdict": "INCONCLUSIVE", "reasons": ["phase2_not_browser_evidence"]},
        "G-COMB": {"verdict": "INCONCLUSIVE", "reasons": ["phase2_not_combined_mission_evidence"]},
    }

    return {
        "experiment_id": "JAR-EXP-0013",
        "phase": "TOOL_MICROBENCH",
        "protocol_revision": protocol.get("revision"),
        "source_execution_id": summary.get("execution_id"),
        "source_state": summary.get("state"),
        "workload_id": summary.get("workload_id"),
        "paired_warm_blocks_analyzed": len(pooled_control),
        "cold_samples_reported": len(cold),
        "contaminated_pairs": contaminated_pairs,
        "duplicate_pair_ids": duplicates,
        "incomplete_pair_ids": sorted(incomplete_pairs),
        "invalid_metric_pair_ids": sorted(invalid_metric_pairs),
        "unverified_treatment_pair_ids": sorted(unverified_treatment_pairs),
        "correctness_failures": declared_failures,
        "cold_samples": cold,
        "operation_warm_effects": operation_effects,
        "overall_warm_effect": overall,
        "tool_overhead_reduction_threshold": required_reduction,
        "g_tr_tool_overhead_component": {
            "verdict": component_verdict,
            "reasons": component_reasons,
        },
        "performance_effects_complete": not incomplete and overall.get("status") == "ESTIMATED",
        "promotion_gate_eligible": False,
        "promotion_gates": promotion_gates,
    }


def render_phase2_report(result: dict) -> str:
    component = result["g_tr_tool_overhead_component"]
    lines = [
        "# JAR-EXP-0013 Phase-2 Tool Microbenchmark Analysis",
        "",
        f"- Source execution: `{result.get('source_execution_id')}`",
        f"- Paired warm blocks analyzed: {result['paired_warm_blocks_analyzed']}",
        f"- Cold samples reported: {result['cold_samples_reported']}",
        f"- Correctness failures: {result['correctness_failures']}",
        f"- G-TR tool-overhead component: {component['verdict']}",
        "- Promotion gate eligible: NO",
        "",
        "## Overall paired warm effect",
    ]
    overall = result["overall_warm_effect"]
    if overall.get("status") == "ESTIMATED":
        lines.append(
            f"- Reduction: {overall['observed_reduction']:.3%} "
            f"(95% CI {overall['ci_low']:.3%} to {overall['ci_high']:.3%})"
        )
    else:
        lines.append(f"- INCONCLUSIVE ({overall.get('reason', 'unavailable')})")

    lines.extend(["", "## Per-operation warm effects"])
    for operation, effect in result["operation_warm_effects"].items():
        lines.append(
            f"- {operation}: {effect['observed_reduction']:.3%} "
            f"(95% CI {effect['ci_low']:.3%} to {effect['ci_high']:.3%}, "
            f"n={effect['paired_blocks']})"
        )

    if component["reasons"]:
        lines.extend(["", "## Component reasons"])
        for reason in component["reasons"]:
            lines.append(f"- {reason}")

    lines.extend(
        [
            "",
            "## Promotion gates",
            "- G-TR: INCONCLUSIVE (tool mission wall-clock and mission-success evidence still required)",
            "- G-OB: INCONCLUSIVE (browser evidence not evaluated in Phase 2)",
            "- G-COMB: INCONCLUSIVE (combined mission evidence not evaluated in Phase 2)",
            "",
            "> Phase-2 tool microbenchmarks can satisfy only the tool-overhead component of G-TR.",
            "> They cannot promote G-TR, G-OB, or G-COMB by themselves.",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_exclusive(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze JAR-EXP-0013 Phase-2 tool microbenchmark evidence."
    )
    parser.add_argument("--summary", required=True, help="Phase-2 summary.json")
    parser.add_argument("--protocol", required=True, help="Frozen protocol.yaml")
    parser.add_argument("--json-output", required=True, help="Exclusive JSON analysis output")
    parser.add_argument("--markdown-output", required=True, help="Exclusive Markdown report output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    with Path(args.summary).open("r", encoding="utf-8") as handle:
        summary = json.load(handle)
    protocol = load_protocol(Path(args.protocol))
    result = analyze_phase2_summary(summary, protocol)
    _write_exclusive(
        Path(args.json_output), json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    _write_exclusive(Path(args.markdown_output), render_phase2_report(result))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
