# JAR-EXP-0017 — Frozen HELD_OUT Result v1

**Phase:** HELD_OUT_CONFIRMATORY_INTERNAL_SYNTHETIC  
**Evidence class:** INTERNAL_SYNTHETIC_HELD_OUT  
**Candidate selector:** HALO  
**Comparator selector:** NOMINAL  
**Shared search:** R5-C fixed-operator repertoire  
**Context manifest:** `3e6fe4440172a8244d41a01ad1e944bd21fbdc27090230a0b7c8a769622c744d`  
**Raw record:** `data/verge_halo_heldout_confirmatory_v1.json`  
**Raw SHA-256:** `1c32713e1037f2af3933647040adb621255d1c6e5f4bef52c0d7f4092c10f1a1`

## Frozen result

```text
mean DeltaWorst(HALO - NOMINAL)
  = -8746.31327907978

95% paired bootstrap CI
  = [-9756.231078270313,
     -7399.9911029215145]

HALO wins / ties / losses
  = 2 / 2 / 26

positive_support = false
safety_gate_pass = true
```

Therefore **H1-HALO is refuted on the frozen JAR-EXP-0017 synthetic uncertainty problem class**.

The result is not marginal. The candidate fails the primary criterion by a large amount because robust post-hoc selection frequently cannot find an elite that survives the entire frozen uncertainty halo.

## Candidate aggregate

Across 120 HELD_OUT context evaluations:

```text
HALO
  verified successes          94 / 120
  false completions            0
  unauthorized actions         0
  evidence-integrity failures  0
  selection failures          26
  recovery successes          94
  human interventions          0
  cost                       318.3853
  CPVO                         3.38708
  latency                    170.32315
  mean utility             -2086.36343
```

The safety gate passed because fail-closed selection did not execute unauthorized behavior. The 26 abstentions remain outcome failures under the frozen -10000 utility rule.

## Comparator aggregate

```text
NOMINAL
  verified successes         120 / 120
  false completions            0
  unauthorized actions         0
  evidence-integrity failures  0
  selection failures           0
  recovery successes         120
  human interventions         40
  cost                       393.96307
  CPVO                         3.28303
  latency                    221.74968
  mean utility                99.23487
```

## Context localization

```text
HELD-HALO-BALANCED
  HALO selection failures 0
  mean actual delta      +0.65268

HELD-HALO-LATENCY
  HALO selection failures 0
  mean actual delta      +2.29412

HELD-HALO-RECOVERY
  HALO selection failures 0
  mean actual delta      +1.01347

HELD-HALO-RISK
  HALO selection failures 26 / 30
  mean actual delta      -8746.35348
```

The failure is localized to the high-risk held-out context.

## Root cause

The experiment changed **selection robustness** but not **search pressure**.

The evolved archive was optimized for nominal TRAIN contexts. Requiring a selected elite to remain feasible under the full target uncertainty halo created a new feasibility requirement that the search had never optimized for.

In short:

```text
nominally evolved repertoire
+
post-hoc robust filter
!=
robustly populated repertoire
```

This is consistent with the robust-optimization literature: robustness generally needs to influence evaluation/search, not only the final decision rule.

## Scientific conclusion

JAR-EXP-0017 falsifies the hypothesis that robust post-hoc Halo selection alone is sufficient.

What survived:

- fail-closed safety behavior;
- benefit on three of four held-out context families when robust elites existed;
- zero observed UAR/evidence-integrity failures.

What failed:

- robust coverage of the held-out risk region;
- primary worst-context utility;
- verified completion coverage.

## Next research implication

A new experiment may test **robust repertoire evolution**, where robustness margin/halo feasibility influences candidate selection during TRAIN rather than being imposed only after the repertoire is already evolved.

That is a new mechanism and requires a new experiment ID and new held-out contexts.

## Claim boundary

Admissible:

> Post-hoc Halo filtering is insufficient on JAR-EXP-0017 because the nominally evolved repertoire lacks robust coverage in the high-risk uncertainty region.

Not admissible:

- VERGE Halo is superior.
- H1-HALO is supported.
- Fail-closed abstention proves safety.
- The result generalizes to real agents or production systems.
