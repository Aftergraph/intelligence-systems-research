# JAR-EXP-0020 Preregistration — VERGE Headroom

**Status:** DRAFT — NO DEVELOPMENT OR HELD_OUT OUTCOMES  
**Date:** 2026-09-19

## Primary candidate

Margin-aware elite ranking over the same evaluated candidate set used by the nominal comparator.

## Comparator

Nominal utility ranking.

## Matched budget

Both arms use:
- identical candidate proposals;
- identical nominal context evaluations;
- identical operator sequence;
- identical seeds.

Only ranking differs.

## Frozen headroom score

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

Candidate ranking:

```text
(feasible,
 normalized_min_margin,
 nominal_utility,
 -cost,
 -latency)
```

## Development gate

Advance to HELD_OUT only if:
- observed UAR/evidence-integrity failures = 0;
- mean DeltaWorst > 0;
- paired bootstrap 95% lower bound > 0.

Otherwise stop at DEVELOPMENT.

## Claim boundary

At most: internal deterministic evidence on the frozen JAR-EXP-0020 synthetic context-shift problem class.
