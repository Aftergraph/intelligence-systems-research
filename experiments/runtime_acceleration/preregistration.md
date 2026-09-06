# JAR-EXP-0013 Preregistration

## Research question

Determine whether ToolRush, Obscura, or their combination materially improve agent-runtime efficiency without reducing correctness, safety, compatibility, or verified mission success.

## Frozen treatments

The four conditions A/B/C/D and exact source revisions are frozen in `protocol.yaml` and `data/runtime_acceleration/manifests/source_pins.json`.

## Confirmatory thresholds

- ToolRush: >=30% aggregate tool-overhead reduction and >=10% tool-heavy mission wall-clock reduction.
- Obscura: >=40% peak browser RSS reduction, >=20% cold-start reduction, >=95% required compatibility.
- Combined: >=15% mission wall-clock reduction.
- Mission-success non-inferiority margin: 5 percentage points absolute for B, C, and D versus A.
- Confirmatory mission floor: 100 verified mission attempts per condition.

The mission floor is a minimum evidence floor, not an automatic pass condition. A gate remains inconclusive when the preregistered 95% confidence requirement is not established, even after the minimum attempt count is reached.

## Statistical analysis contract

Protocol revision 3 freezes the confirmatory statistical rules before any controlled-host performance result is collected:

- confidence level: 95%;
- paired timing/effect intervals: paired percentile bootstrap preserving paired-block identity;
- bootstrap resamples: 10,000;
- bootstrap seed: `130013`;
- mission-success difference interval: Newcombe/Wilson treatment-minus-control interval;
- promotion requires the lower bound of the 95% interval to meet the effect threshold;
- mission-success non-inferiority requires the lower bound of the treatment-minus-control success interval to be no worse than `-0.05`.

A point estimate above a promotion threshold is not sufficient when its 95% interval crosses below that threshold. Such a result is `INCONCLUSIVE`, not `PASS`. A point estimate below a frozen threshold is `FAIL`. A confidence interval entirely below the non-inferiority margin is `FAIL`; an interval that crosses the margin is `INCONCLUSIVE`.

## Controlled-host preflight

Protocol revision 2 froze the host contamination limits before any controlled-host performance data was collected, and revision 3 preserves them unchanged:

- CPU utilization: <=20.0% before a confirmatory timing block.
- Memory utilization: <=80.0% before a confirmatory timing block.
- AC power: required.

A contaminated block remains in raw evidence and is excluded from confirmatory timing summaries according to the preregistered rule. Host-local configuration may identify executable and checkout paths, but it may not weaken these limits.

## Pre-data amendment A1 — 2026-09-06

Revision 1 specified that preflight limits must be preregistered but did not encode their numeric values in `protocol.yaml`. Revision 2 closes that artifact-contract omission by adding the values above. This amendment occurred before the first controlled-host performance run and before any ToolRush, Obscura, combined, browser, trace-replay, or mission performance result was collected by JAR-EXP-0013. Treatment pins, hypotheses, promotion thresholds, mission floor, non-inferiority margin, workloads, and analysis gates are unchanged.

## Pre-data amendment A2 — 2026-09-06

Revision 3 closes two statistical-contract weaknesses identified during pre-run performance review: the prior bootstrap helper did not preserve paired-block identity, and promotion logic could evaluate point estimates without requiring confidence evidence. Revision 3 adds paired bootstrap intervals, a fixed bootstrap seed and resample count, explicit 95% lower-bound promotion rules, Newcombe/Wilson mission-success difference intervals, and an explicit ToolRush non-inferiority requirement. No treatment pin, workload, effect threshold, non-inferiority margin, host limit, or success criterion was relaxed. This amendment was committed before the first controlled-host performance observation.

## Invalid promotion conditions

Any new treatment-induced correctness failure, safety-boundary regression, silent unsupported-feature success, post-hoc threshold lowering, unrecorded statistical-rule change, or unrecorded preflight-rule change invalidates promotion.

## Performance host

Primary performance evidence must come from a controlled Windows Hermes host. Hosted CI provides functional reproducibility only.
