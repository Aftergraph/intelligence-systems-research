# JAR-EXP-0022 — VERGE Traceglass

**Title:** Fixed-Label Execution-Trace Readiness for Out-of-Simulator Headroom Evaluation  
**Status:** EVIDENCE-READINESS STUDY  
**Parent evidence:** JAR-EXP-0021 internal implementation replication  
**Canonical owner:** Aftergraph/intelligence-systems-research

## Objective

Determine whether existing non-synthetic Aftergraph execution evidence is sufficient to evaluate the frozen VERGE Headroom ranking mechanism without inventing labels after outcome inspection.

This study does **not** run paid providers and does not mutate production systems.

## Required corpus contract

A Headroom-compatible trace record must bind, before ranking:

- immutable trace/run identity;
- execution/evidence class;
- workload/context identity;
- policy configuration:
  - confidence threshold;
  - verification depth;
  - retry ceiling;
- context requirements:
  - minimum confidence;
  - minimum verification depth;
  - minimum retry/recovery allowance;
- fixed outcome labels:
  - verified success;
  - false completion;
  - unauthorized action;
  - evidence-integrity failure;
  - cost;
  - latency;
  - human intervention count;
- provenance:
  - source artifact;
  - source hash or immutable commit;
  - provider/runtime identity where applicable.

## Admission classes

```text
TRACE_COMPATIBLE
TRACE_INCOMPLETE
SIMULATION_ONLY
FIXTURE_ONLY
INFRASTRUCTURE_ONLY
PROVIDER_LIVE_PARTIAL
```

Only `TRACE_COMPATIBLE` records may enter an out-of-simulator Headroom comparison.

## Known candidate sources to audit

- JAR-EXP-0013 controlled-host trace replay artifacts;
- STUDY-008 live benchmark artifacts;
- STUDY-011 run records;
- durability / assurance raw evidence;
- any committed runtime trajectory/evidence records discoverable in the canonical ISR repository.

## Fail-closed rule

Missing policy-margin fields cannot be inferred from outcome, condition name, model identity, or prose.

If an artifact lacks the frozen pre-action policy configuration or context thresholds, it is not Headroom-compatible.

## Primary result

A machine-readable readiness report:

```text
source
→ evidence class
→ required fields present/missing
→ admissible yes/no
→ reason
```

No performance hypothesis is tested in JAR-EXP-0022.

## Promotion condition

Proceed to an out-of-simulator Headroom replay only if at least one corpus contains enough immutable records to form both ranking arms without reconstructing policy labels post hoc.

Otherwise the study closes with a concrete instrumentation/schema gap and the next work moves to Runtime/WORKS evidence capture rather than fabricating a corpus.
