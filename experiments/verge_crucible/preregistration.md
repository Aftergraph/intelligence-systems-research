# JAR-EXP-0019 Preregistration — VERGE Crucible

**Status:** DRAFT — NO HELD_OUT OUTCOMES  
**Date:** 2026-09-19

## Candidate

Multi-fidelity robust repertoire search.

Per TRAIN niche and seed:

1. generate/evaluate 144 candidate genomes nominally;
2. keep nominally feasible candidates;
3. rank by nominal utility;
4. promote top 16 nominally feasible candidate evaluations;
5. evaluate the remaining 7 points of the frozen 8-point training halo;
6. robust-feasible requires feasibility on all 8 points;
7. source elite ranks by worst halo utility, then mean halo utility.

## Comparator

Nominal repertoire search using 256 nominal candidate evaluations per TRAIN niche.

## Budget equality

Both arms consume exactly 256 policy-context evaluations per TRAIN niche.

## Search seeds

30 seeds: 0..29.

## Training halo

```text
confidence shocks = [0.00, 0.02]
latency shocks    = [0.00, 0.08]
cost shocks       = [0.00, 0.08]
```

## Development gate

HELD_OUT is not executed unless DEVELOPMENT shows:
- safety gate pass;
- positive mean DeltaWorst;
- paired bootstrap lower bound > 0.

Otherwise JAR-EXP-0019 stops at DEVELOPMENT.

## Safety

Observed candidate:
- UAR = 0;
- evidence-integrity failures = 0.

Fail-closed target selection remains data with utility -10000.

## Claim boundary

Maximum claim is internal deterministic synthetic evidence on the frozen JAR-EXP-0019 problem class.


## Pre-development implementation clarification

Promotion operates on candidate evaluations rather than deduplicated genome identities.

Repeated genomes remain legitimate evaluated candidates and consume robustness budget if they rank in the top 16. This rule is frozen before the first DEVELOPMENT run and avoids introducing an unregistered resampling procedure when nominal search converges to the same genotype.
