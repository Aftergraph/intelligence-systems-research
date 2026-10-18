# JAR-EXP-0015 Pre-Implementation Review

**Scope:** VERGE design and preregistration  
**Reviewed branch:** research/jar-exp-0015-verge-evolution  
**Reviewed head:** ca9986eef623bc4d4dc722972bb159b8041b749f

## Verdict

Design is suitable for an offline implementation slice, but confirmatory execution still has open methodology gates.

## Open findings

1. **Primary rule:** freeze one exact primary statistical decision rule before confirmatory execution.
2. **Baseline selection:** freeze development and confirmatory partitions separately and record baseline selection before confirmatory evaluation.
3. **Representation mismatch:** CMA-ES and Differential Evolution are numeric-subspace comparators, not whole-policy comparators.
4. **Zero-event wording:** report observed event counts and confidence bounds; zero observed events is not proof of zero population risk.
5. **QD sparsity:** begin with 2–3 behavior descriptors or a bounded archive rather than all eight proposed dimensions.
6. **Adaptive operator attribution:** persist every probability update and compare with a fixed-probability ablation.
7. **LLM variation confounding:** keep the first deterministic slice network-free; pin provider/model/prompt/costs in any later LLM arm.
8. **Economic fairness:** report both equal-evaluation and cost-normalized comparisons.
9. **Benchmark integrity:** freeze benchmark, verifier, exclusion, and analysis hashes outside candidate control.
10. **Power:** >=30 seeds is an implementation default, not a confirmatory power justification; freeze a proper power plan before outcome inspection.

## First implementation slice

```text
offline S1/S2 harness
+ non-LLM operators
+ 2–3 QD descriptors
+ immutable benchmark hashes
+ exact lineage receipts
+ B0/B1/B2/B5/B6
+ B8/B9/B10/B11 ablations
```

Deferred:
- LLM semantic mutation
- real-agent S3 execution
- provider comparisons
- production integration

## Gate state

- Offline implementation: READY after design review
- Deterministic exploratory execution: implementation absent
- Confirmatory execution: blocked by unresolved statistical freeze items
- S3 real-agent execution: separately protected
- Production integration: out of scope
