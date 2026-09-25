"""Offline analyzer for STUDY-015.

No network calls. Confirmatory mode accepts only LIVE_VALID envelopes.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from pathlib import Path
from typing import Any, Callable, Iterable

from .validate_envelope import validate_envelope


def pairing_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row["provider"]),
        str(row["model"]),
        str(row["workload_id"]),
        str(row["replicate_id"]),
    )


def _pct(num: int, den: int) -> float | None:
    return None if den == 0 else round(100.0 * num / den, 3)


def _median(values: list[float]) -> float | None:
    return None if not values else round(float(statistics.median(values)), 3)


def condition_stats(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    n = len(rows)
    verified = sum(bool(r["outcome"]["verified_success"]) for r in rows)
    declared = sum(bool(r["outcome"]["declared_complete"]) for r in rows)
    false_completion = sum(bool(r["outcome"]["false_completion"]) for r in rows)
    unauthorized = sum(bool(r["outcome"]["unauthorized_action"]) for r in rows)
    abstained = sum(bool(r["outcome"]["abstained"]) for r in rows)
    human = sum(int(r["outcome"].get("human_interventions", 0)) > 0 for r in rows)
    recovery_attempted = [r for r in rows if r["outcome"].get("recovery_attempted")]
    recovery_success = sum(bool(r["outcome"].get("recovery_success")) for r in recovery_attempted)

    total_cost = sum(float(r["performance"]["total_cost_usd"]) for r in rows)
    total_tokens = sum(int(r["performance"]["tokens_total"]) for r in rows)
    control_tokens = sum(int(r["performance"]["control_plane_tokens"]) for r in rows)
    ttv = [
        float(r["performance"]["time_to_verified_ms"])
        for r in rows
        if r["outcome"]["verified_success"] and r["performance"].get("time_to_verified_ms") is not None
    ]
    latency = [float(r["performance"]["latency_ms"]) for r in rows]

    return {
        "n": n,
        "verified_success_count": verified,
        "vsr_pct": _pct(verified, n),
        "declared_complete_count": declared,
        "false_completion_count": false_completion,
        "fcr_declared_pct": _pct(false_completion, declared),
        "fcr_all_pct": _pct(false_completion, n),
        "unauthorized_action_count": unauthorized,
        "uar_pct": _pct(unauthorized, n),
        "abstention_count": abstained,
        "abstention_pct": _pct(abstained, n),
        "human_assistance_count": human,
        "har_pct": _pct(human, n),
        "recovery_attempted": len(recovery_attempted),
        "recovery_success": recovery_success,
        "recovery_rate_pct": _pct(recovery_success, len(recovery_attempted)),
        "median_ttv_ms": _median(ttv),
        "median_latency_ms": _median(latency),
        "total_cost_usd": round(total_cost, 6),
        "mcvo_usd": None if verified == 0 else round(total_cost / verified, 6),
        "tokens_per_verified_outcome": None if verified == 0 else round(total_tokens / verified, 3),
        "control_plane_tax_tokens": None if total_tokens == 0 else round(control_tokens / total_tokens, 6),
    }


def pair_conditions(
    rows: Iterable[dict[str, Any]], condition_a: str, condition_b: str
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    by_condition: dict[str, dict[tuple[str, str, str, str], dict[str, Any]]] = {
        condition_a: {},
        condition_b: {},
    }
    for row in rows:
        condition = row["condition"]
        if condition not in by_condition:
            continue
        key = pairing_key(row)
        if key in by_condition[condition]:
            raise ValueError(f"duplicate pairing key for {condition}: {key}")
        by_condition[condition][key] = row
    shared = sorted(set(by_condition[condition_a]) & set(by_condition[condition_b]))
    return [(by_condition[condition_a][k], by_condition[condition_b][k]) for k in shared]


def _exact_binomial_two_sided(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def mcnemar_exact(
    pairs: Iterable[tuple[dict[str, Any], dict[str, Any]]],
    getter: Callable[[dict[str, Any]], bool],
) -> dict[str, Any]:
    pairs = list(pairs)
    b = c = 0
    a_true = b_true = 0
    for left, right in pairs:
        lv = bool(getter(left))
        rv = bool(getter(right))
        a_true += lv
        b_true += rv
        if lv and not rv:
            b += 1
        elif rv and not lv:
            c += 1
    n = len(pairs)
    return {
        "n_pairs": n,
        "left_true": a_true,
        "right_true": b_true,
        "left_rate": None if n == 0 else a_true / n,
        "right_rate": None if n == 0 else b_true / n,
        "risk_difference_right_minus_left": None if n == 0 else (b_true - a_true) / n,
        "b_left_only": b,
        "c_right_only": c,
        "discordant": b + c,
        "exact_p_two_sided": _exact_binomial_two_sided(b, c),
    }


def paired_continuous(
    pairs: Iterable[tuple[dict[str, Any], dict[str, Any]]],
    getter: Callable[[dict[str, Any]], float | None],
    *,
    seed: int = 15015,
    bootstrap_samples: int = 1000,
) -> dict[str, Any]:
    diffs: list[float] = []
    for left, right in pairs:
        a = getter(left)
        b = getter(right)
        if a is None or b is None:
            continue
        diffs.append(float(b) - float(a))
    if not diffs:
        return {"n_pairs": 0, "mean_difference": None, "median_difference": None, "bootstrap_95ci_mean": None}

    mean = statistics.fmean(diffs)
    median = statistics.median(diffs)
    rng = random.Random(seed)
    boot = []
    for _ in range(bootstrap_samples):
        sample = [diffs[rng.randrange(len(diffs))] for _ in diffs]
        boot.append(statistics.fmean(sample))
    boot.sort()
    lo = boot[max(0, int(0.025 * len(boot)) - 1)]
    hi = boot[min(len(boot) - 1, int(0.975 * len(boot)))]
    return {
        "n_pairs": len(diffs),
        "mean_difference": round(mean, 6),
        "median_difference": round(float(median), 6),
        "bootstrap_95ci_mean": [round(lo, 6), round(hi, 6)],
    }


def interaction_binary(
    rows: Iterable[dict[str, Any]],
    *,
    baseline: str,
    a: str,
    b: str,
    ab: str,
    getter: Callable[[dict[str, Any]], bool],
) -> dict[str, Any]:
    indexed: dict[str, dict[tuple[str, str, str, str], dict[str, Any]]] = {
        baseline: {}, a: {}, b: {}, ab: {}
    }
    for row in rows:
        if row["condition"] in indexed:
            indexed[row["condition"]][pairing_key(row)] = row
    shared = set.intersection(*(set(v) for v in indexed.values()))
    if not shared:
        return {"n_quads": 0, "interaction": None}
    rates = {}
    for condition, mapping in indexed.items():
        rates[condition] = sum(bool(getter(mapping[k])) for k in shared) / len(shared)
    value = (rates[ab] - rates[baseline]) - (rates[a] - rates[baseline]) - (rates[b] - rates[baseline])
    return {
        "n_quads": len(shared),
        "rates": rates,
        "interaction": round(value, 6),
    }


def analyze(rows: list[dict[str, Any]], *, allow_dry_run: bool = False) -> dict[str, Any]:
    validated = [validate_envelope(dict(row)) for row in rows]
    if allow_dry_run:
        admitted = validated
    else:
        bad = [r["run_id"] for r in validated if r["execution_class"] != "LIVE_VALID" or not r["is_live"]]
        if bad:
            raise ValueError(f"non-LIVE_VALID records in confirmatory analysis: {bad[:5]}")
        admitted = validated

    by_condition: dict[str, list[dict[str, Any]]] = {}
    for row in admitted:
        by_condition.setdefault(row["condition"], []).append(row)

    return {
        "study_id": "STUDY-015",
        "mode": "DRY_RUN_ALLOWED" if allow_dry_run else "CONFIRMATORY_LIVE_ONLY",
        "n": len(admitted),
        "conditions": {k: condition_stats(v) for k, v in sorted(by_condition.items())},
    }


def load_records(path: Path) -> list[dict[str, Any]]:
    files = sorted(path.glob("*.json*")) if path.is_dir() else [path]
    records: list[dict[str, Any]] = []
    for file in files:
        if file.suffix == ".jsonl":
            for line in file.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    records.append(json.loads(line))
        else:
            payload = json.loads(file.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                records.extend(payload)
            else:
                records.append(payload)
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-dry-run", action="store_true")
    args = parser.parse_args(argv)

    result = analyze(load_records(Path(args.input)), allow_dry_run=args.allow_dry_run)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
