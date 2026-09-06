# JAR-EXP-0013 — Agent Runtime Acceleration

This package evaluates ToolRush and Obscura in a frozen 2×2 factorial design against stock Hermes + Chromium.

The harness is research-only. It does not alter WORKS, Trust Gateway, AIE, governance contracts, or production gateway configuration.

## Conditions

- A: stock Hermes + Chromium
- B: ToolRush + Chromium
- C: stock Hermes + Obscura
- D: ToolRush + Obscura

## Evidence rule

Microbenchmarks are diagnostic. Promotion decisions require verifier-backed mission outcomes and the thresholds frozen in `protocol.yaml`. GitHub-hosted runner timings are never authoritative performance evidence.

## Controlled-host preflight

Confirmatory timing blocks must capture host load before execution and evaluate the frozen contamination limits with `check_preflight`. Contaminated blocks stay in raw evidence but are excluded from confirmatory timing summaries according to the preregistered rule.

CI runs the deterministic functional suite on Windows and Ubuntu. CI timing itself is not performance evidence.
