# JAR-EXP-0013 Preregistration

## Research question

Determine whether ToolRush, Obscura, or their combination materially improve agent-runtime efficiency without reducing correctness, safety, compatibility, or verified mission success.

## Frozen treatments

The four conditions A/B/C/D and exact source revisions are frozen in `protocol.yaml` and `data/runtime_acceleration/manifests/source_pins.json`.

## Confirmatory thresholds

- ToolRush: >=30% aggregate tool-overhead reduction and >=10% tool-heavy mission wall-clock reduction.
- Obscura: >=40% peak browser RSS reduction, >=20% cold-start reduction, >=95% required compatibility.
- Combined: >=15% mission wall-clock reduction.
- Mission-success non-inferiority margin: 5 percentage points absolute.
- Confirmatory mission floor: 100 verified mission attempts per condition.

## Controlled-host preflight

Protocol revision 2 freezes the host contamination limits before any controlled-host performance data is collected:

- CPU utilization: <=20.0% before a confirmatory timing block.
- Memory utilization: <=80.0% before a confirmatory timing block.
- AC power: required.

A contaminated block remains in raw evidence and is excluded from confirmatory timing summaries according to the preregistered rule. Host-local configuration may identify executable and checkout paths, but it may not weaken these limits.

## Pre-data amendment A1 — 2026-09-06

Revision 1 specified that preflight limits must be preregistered but did not encode their numeric values in `protocol.yaml`. Revision 2 closes that artifact-contract omission by adding the values above. This amendment occurred before the first controlled-host performance run and before any ToolRush, Obscura, combined, browser, trace-replay, or mission performance result was collected by JAR-EXP-0013. Treatment pins, hypotheses, promotion thresholds, mission floor, non-inferiority margin, workloads, and analysis gates are unchanged.

## Invalid promotion conditions

Any new treatment-induced correctness failure, safety-boundary regression, silent unsupported-feature success, post-hoc threshold lowering, or unrecorded preflight-rule change invalidates promotion.

## Performance host

Primary performance evidence must come from a controlled Windows Hermes host. Hosted CI provides functional reproducibility only.
