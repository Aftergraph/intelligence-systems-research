from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis.analyze import paired_bootstrap_median_reduction
from .protocol import load_protocol

_EXPECTED_CONDITIONS = ("A", "B", "C", "D")
_TRACE_METRICS = {
    "tool_time_A_vs_B": ("A", "B", "tool_time_total_ms"),
    "browser_time_A_vs_C": ("A", "C", "browser_time_total_ms"),
    "trace_wall_A_vs_D": ("A", "D", "trace_wall_clock_ms"),
}


def _require_mapping(value, label: str) -> dict:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a mapping")
    return value


def _group_pairs(summary: dict) -> list[tuple[str, dict[str, dict]]]:
    runs = summary.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("Phase-1 summary has no completed runs")

    grouped: dict[str, dict[str, dict]] = {}
    counts: dict[str, int] = {}
    for raw in runs:
        run = _require_mapping(raw, "run")
        pair_id = run.get("pair_id")
        condition = run.get("condition")
        if not isinstance(pair_id, str) or not pair_id:
            raise ValueError("every Phase-1 run requires a pair_id")
        if condition not in _EXPECTED_CONDITIONS:
            raise ValueError(f"invalid Phase-1 condition: {condition}")
        counts[pair_id] = counts.get(pair_id, 0) + 1
        grouped.setdefault(pair_id, {})[condition] = run

    pairs: list[tuple[str, dict[str, dict]]] = []
    for pair_id, by_condition in grouped.items():
        if counts[pair_id] != 4 or set(by_condition) != set(_EXPECTED_CONDITIONS):
            raise ValueError(f"paired block {pair_id} must contain A/B/C/D exactly once")
        pairs.append((pair_id, by_condition))

    clean_pairs = summary.get("clean_pairs")
    if clean_pairs is not None and int(clean_pairs) != len(pairs):
        raise ValueError("Phase-1 clean_pairs does not match completed paired blocks")
    return pairs


def _metric_or_none(run: dict, name: str) -> float | None:
    metrics = run.get("metrics")
    if not isinstance(metrics, dict):
        return None
    value = metrics.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if value <= 0.0:
        return None
    return value


def _verified(run: dict) -> bool:
    verifier = _require_mapping(run.get("verifier"), "run verifier")
    return verifier.get("verified") is True


def _inconclusive_effect(
    *,
    control_condition: str,
    treatment_condition: str,
    metric_name: str,
    paired_blocks: int,
) -> dict:
    return {
        "status": "INCONCLUSIVE",
        "reason": "invalid_or_missing_metric",
        "control_condition": control_condition,
        "treatment_condition": treatment_condition,
        "metric": metric_name,
        "paired_blocks": paired_blocks,
        "confidence_level": 0.95,
        "method": "paired_percentile_bootstrap",
    }


def analyze_phase1_summary(summary: dict, protocol: dict) -> dict:
    """Analyze deterministic Phase-1 trace evidence without evaluating promotion gates."""
    summary = _require_mapping(summary, "summary")
    protocol = _require_mapping(protocol, "protocol")
    if summary.get("experiment_id") != "JAR-EXP-0013" or protocol.get("experiment_id") != "JAR-EXP-0013":
        raise ValueError("unexpected JAR-EXP-0013 experiment identity")
    if summary.get("phase") != "TRACE_REPLAY":
        raise ValueError("Phase-1 analysis requires TRACE_REPLAY evidence")

    analysis = _require_mapping(protocol.get("analysis"), "protocol analysis")
    if analysis.get("effect_interval_method") != "paired_percentile_bootstrap":
        raise ValueError("Phase-1 analysis requires paired_percentile_bootstrap")
    if float(analysis.get("confidence_level", 0.0)) != 0.95:
        raise ValueError("Phase-1 analyzer is frozen to the preregistered 95% interval")
    seed = int(analysis["bootstrap_seed"])
    resamples = int(analysis["bootstrap_resamples"])
    if resamples < 1:
        raise ValueError("bootstrap_resamples must be >= 1")

    pairs = _group_pairs(summary)
    effects: dict[str, dict] = {}
    for effect_name, (control_condition, treatment_condition, metric_name) in _TRACE_METRICS.items():
        control = [_metric_or_none(by_condition[control_condition], metric_name) for _, by_condition in pairs]
        treatment = [_metric_or_none(by_condition[treatment_condition], metric_name) for _, by_condition in pairs]
        if any(value is None for value in control) or any(value is None for value in treatment):
            effects[effect_name] = _inconclusive_effect(
                control_condition=control_condition,
                treatment_condition=treatment_condition,
                metric_name=metric_name,
                paired_blocks=len(pairs),
            )
            continue

        effect = paired_bootstrap_median_reduction(
            [float(value) for value in control],
            [float(value) for value in treatment],
            seed=seed,
            resamples=resamples,
        )
        effect.update(
            {
                "status": "ESTIMATED",
                "control_condition": control_condition,
                "treatment_condition": treatment_condition,
                "metric": metric_name,
                "paired_blocks": len(pairs),
                "confidence_level": 0.95,
            }
        )
        effects[effect_name] = effect

    verification_rate = {}
    derived_correctness_failures = 0
    for condition in _EXPECTED_CONDITIONS:
        values = [_verified(by_condition[condition]) for _, by_condition in pairs]
        verification_rate[condition] = sum(values) / len(values)
        if condition != "A":
            derived_correctness_failures += sum(not value for value in values)

    declared_failures = int(summary.get("correctness_failures", derived_correctness_failures))
    if declared_failures != derived_correctness_failures:
        raise ValueError("Phase-1 correctness_failures does not match run verifier evidence")

    gates = {
        gate: {"verdict": "INCONCLUSIVE", "reasons": ["phase1_trace_only"]}
        for gate in ("G-TR", "G-OB", "G-COMB")
    }
    return {
        "experiment_id": "JAR-EXP-0013",
        "phase": "TRACE_REPLAY",
        "protocol_revision": protocol.get("revision"),
        "source_execution_id": summary.get("execution_id"),
        "source_state": summary.get("state"),
        "paired_blocks_analyzed": len(pairs),
        "contaminated_pairs": int(summary.get("contaminated_pairs", 0)),
        "correctness_failures": derived_correctness_failures,
        "verification_rate": verification_rate,
        "effects": effects,
        "performance_effects_complete": all(
            effect.get("status") == "ESTIMATED" for effect in effects.values()
        ),
        "promotion_gate_eligible": False,
        "promotion_gates": gates,
    }


def render_phase1_report(result: dict) -> str:
    lines = [
        "# JAR-EXP-0013 Phase-1 Trace Analysis",
        "",
        f"- Source execution: `{result.get('source_execution_id')}`",
        f"- Paired blocks analyzed: {result['paired_blocks_analyzed']}",
        f"- Correctness failures: {result['correctness_failures']}",
        f"- Performance effects complete: {'YES' if result['performance_effects_complete'] else 'NO'}",
        "- Promotion gate eligible: NO",
        "",
        "## Verification rate",
    ]
    for condition in _EXPECTED_CONDITIONS:
        lines.append(f"- {condition}: {result['verification_rate'][condition]:.3f}")

    lines.extend(["", "## Paired trace effects"])
    for name, effect in result["effects"].items():
        if effect.get("status") == "ESTIMATED":
            lines.append(
                f"- {name}: {effect['observed_reduction']:.3%} "
                f"(95% CI {effect['ci_low']:.3%} to {effect['ci_high']:.3%})"
            )
        else:
            lines.append(f"- {name}: INCONCLUSIVE ({effect.get('reason', 'unavailable')})")

    lines.extend(["", "## Promotion gates"])
    for gate in ("G-TR", "G-OB", "G-COMB"):
        verdict = result["promotion_gates"][gate]
        lines.append(f"- {gate}: {verdict['verdict']} ({', '.join(verdict['reasons'])})")
    lines.extend(
        [
            "",
            "> Phase-1 deterministic trace evidence is diagnostic performance evidence only.",
            "> It cannot promote G-TR, G-OB, or G-COMB without the preregistered later-phase evidence.",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_exclusive(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze JAR-EXP-0013 Phase-1 trace evidence.")
    parser.add_argument("--summary", required=True, help="Phase-1 summary.json")
    parser.add_argument("--protocol", required=True, help="Frozen protocol.yaml")
    parser.add_argument("--json-output", required=True, help="Exclusive JSON analysis output")
    parser.add_argument("--markdown-output", required=True, help="Exclusive Markdown report output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    with Path(args.summary).open("r", encoding="utf-8") as handle:
        summary = json.load(handle)
    protocol = load_protocol(Path(args.protocol))
    result = analyze_phase1_summary(summary, protocol)
    _write_exclusive(Path(args.json_output), json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_exclusive(Path(args.markdown_output), render_phase1_report(result))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
