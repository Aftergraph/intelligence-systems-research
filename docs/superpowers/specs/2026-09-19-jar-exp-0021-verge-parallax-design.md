# JAR-EXP-0021 — VERGE Parallax

**Title:** Independent-Code-Path Reproduction of Headroom Ranking  
**Status:** INTERNAL REPLICATION  
**Parent evidence:** JAR-EXP-0020 frozen HELD_OUT support  
**Canonical owner:** Aftergraph/intelligence-systems-research

## Objective

Test whether the JAR-EXP-0020 Headroom result survives an independently implemented ranking path derived only from the frozen written specification.

This is **not** an external independent reproduction. It is an internal implementation-path replication intended to detect coding-path dependence in the original Headroom implementation.

## Replication boundary

The replica may reuse:
- frozen context manifests;
- deterministic candidate generation;
- shared PolicyGenome and evaluator contracts.

The replica must **not** import or call:
- `experiments.verge_headroom.ranking`;
- original Headroom selector helpers;
- original confirmatory ranking implementation.

## Frozen ranking specification

For each feasible candidate:

```text
confidence_margin = confidence_threshold - min_confidence
verification_margin = verification_depth - min_verification
retry_margin = retry_ceiling - min_retries

normalized_min_margin =
  min(
    confidence_margin / 0.10,
    verification_margin / 2.0,
    retry_margin / 2.0
  )
```

Replica candidate ordering:

```text
(
  feasible,
  normalized_min_margin,
  nominal_utility,
  -cost,
  -latency,
  stable_candidate_id
)
```

Comparator ordering:

```text
(
  feasible,
  nominal_utility,
  -cost,
  -latency,
  stable_candidate_id
)
```

## Primary replication tests

1. On every frozen JAR-EXP-0020 TRAIN seed/niche candidate set, replica and original Headroom must select the same candidate identity.
2. Replica rerun of the frozen JAR-EXP-0020 HELD_OUT protocol must reproduce:
   - seed-level DeltaWorst vector;
   - mean DeltaWorst;
   - bootstrap interval;
   - safety totals;
   - positive-support verdict.
3. Raw reproduction artifact is hash-bound.

## Claim boundary

Passing this study supports only:

> JAR-EXP-0020 is reproducible through a second internal implementation path.

It is not an external independent reproduction and does not establish live-agent generalization.
