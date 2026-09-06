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

## Invalid promotion conditions

Any new treatment-induced correctness failure, safety-boundary regression, silent unsupported-feature success, or post-hoc threshold lowering invalidates promotion.

## Performance host

Primary performance evidence must come from a controlled Windows Hermes host. Hosted CI provides functional reproducibility only.
