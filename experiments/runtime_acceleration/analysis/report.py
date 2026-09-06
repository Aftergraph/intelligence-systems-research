from __future__ import annotations


def render_gate_report(verdicts: dict) -> str:
    lines = ["# JAR-EXP-0013 Gate Verdicts", ""]
    for gate in ("G-TR", "G-OB", "G-COMB"):
        result = verdicts[gate]
        lines.append(f"- **{gate}: {result['verdict']}**")
        for reason in result.get("reasons", []):
            lines.append(f"  - {reason}")
    return "\n".join(lines) + "\n"
