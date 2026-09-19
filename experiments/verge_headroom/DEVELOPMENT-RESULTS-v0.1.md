# JAR-EXP-0020 — DEVELOPMENT Result v0.1

**Phase:** DEVELOPMENT ONLY  
**Evidence class:** EXPLORATORY_DEVELOPMENT  
**HELD_OUT evaluated:** NO  
**Context manifest:** `f7254066ec066442949408006c8f6f6e97d3c6461a4257d38dc261754de3c962`  
**Raw record:** `data/verge_headroom_dev_v0_1.json`  
**Raw SHA-256:** `316e061fa382cee70c6e4b95de5f7c328fc35c1cf8a65796d2131e261eedd8ae`

## Frozen DEVELOPMENT setup

- 30 seeds.
- 8 TRAIN contexts.
- 4 DEVELOPMENT contexts.
- 256 nominal candidate evaluations per TRAIN niche.
- Candidate and comparator used the **same evaluated candidate set** within each seed/niche.
- Same operators, seeds, proposals and evaluation cost.
- Only elite ranking differed.
- HELD_OUT was not evaluated.

## Primary DEVELOPMENT endpoint

```text
mean DeltaWorst(Headroom - Nominal)
  = +3.7803595923604756

95% paired bootstrap CI
  = [+2.1533354911481535,
     +5.4224064633666265]

wins / ties / losses
  = 14 / 7 / 9
```

The preregistered DEVELOPMENT gate passed.

## Safety and completion

Across 120 DEVELOPMENT context evaluations per arm:

```text
HEADROOM
  verified               120 / 120
  UAR                       0
  evidence failures         0
  selection failures        0

NOMINAL
  verified               120 / 120
  UAR                       0
  evidence failures         0
  selection failures        0
```

## Secondary development trade-offs

```text
HEADROOM
  mean utility         101.15092320528508
  cost                 410.594064
  CPVO                    3.4216172
  latency               262.1311078631628
  human interventions    15

NOMINAL
  mean utility         100.40978413621797
  cost                 369.27624
  CPVO                    3.077302
  latency               197.04063861537924
  human interventions    28
```

Headroom improves the frozen worst-context DEVELOPMENT endpoint and reduces interventions, but pays more cost and latency.

## Context localization

```text
DEV-HDR-BAL   mean delta  +0.32922
DEV-HDR-LAT   mean delta  -0.34657
DEV-HDR-REC   mean delta  +4.78088
DEV-HDR-RISK  mean delta  -1.79899
```

The primary improvement is not uniform across context families.

## Decision

Proceed to the already-frozen HELD_OUT context set **without changing the mechanism**.

No changes to:
- margin normalization;
- ranking order;
- candidate generation;
- seeds;
- budget;
- context definitions;
- safety semantics

are permitted before the HELD_OUT run.

## Claim boundary

This DEVELOPMENT result authorizes only the next internal synthetic held-out test.
