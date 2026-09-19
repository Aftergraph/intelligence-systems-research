# JAR-EXP-0020 — Frozen HELD_OUT Result v1

**Phase:** HELD_OUT_CONFIRMATORY_INTERNAL_SYNTHETIC  
**Evidence class:** INTERNAL_SYNTHETIC_HELD_OUT  
**Candidate:** HEADROOM-RANK  
**Comparator:** NOMINAL-RANK  
**Context manifest:** `f7254066ec066442949408006c8f6f6e97d3c6461a4257d38dc261754de3c962`  
**Raw record:** `data/verge_headroom_heldout_confirmatory_v1.json`  
**Raw SHA-256:** `11e6c0d4e66584f407e7e784b65afe9f985d12478cc3016e2dc559131b83bc4c`

## Frozen primary result

```text
mean DeltaWorst(Headroom - Nominal)
  = +3.843189264168792

95% paired bootstrap CI
  = [+2.240316653152203,
     +5.452553729161985]

wins / ties / losses
  = 17 / 11 / 2

positive_support = true
safety_gate_pass = true
```

The preregistered primary criterion is satisfied.

## Safety and verified completion

Across 120 HELD_OUT context evaluations:

```text
HEADROOM
  verified successes          120 / 120
  false completions             0
  unauthorized actions          0
  evidence-integrity failures   0
  selection failures            0

NOMINAL
  verified successes          120 / 120
  false completions             0
  unauthorized actions          0
  evidence-integrity failures   0
  selection failures            0
```

The candidate passed the frozen operational safety gate.

This finite deterministic result is not proof of zero population-level risk.

## Secondary trade-offs

```text
HEADROOM
  mean utility          100.54883943953854
  cost                  473.066508
  CPVO                     3.9422209
  latency                281.19744982149984
  human interventions     18

NOMINAL
  mean utility           99.1765701873532
  cost                  426.14988
  CPVO                     3.551249
  latency                212.48659807046488
  human interventions     39
```

Headroom improves the frozen worst-context endpoint and reduces interventions, but costs more and is slower.

## Context-level actual-target deltas

```text
HELD-HDR-BAL   +0.62830
HELD-HDR-LAT   +1.26896
HELD-HDR-REC   +5.07156
HELD-HDR-RISK  -1.47974
```

The gain is therefore not uniform across context families.

## Negative seeds

Two seed-level primary losses occurred:

```text
seed 3   DeltaWorst = -0.40730239389749556
seed 15  DeltaWorst = -0.40730239389749556
```

These do not invalidate the frozen primary test because the paired bootstrap interval remains strictly positive.

## Scientific conclusion

JAR-EXP-0020 provides the first preregistered internal held-out support in the VERGE sequence for a mechanism-specific hypothesis:

> among already-feasible policies generated under the same search/evaluation budget, selecting source elites by frozen feasibility headroom before nominal utility improves worst-context utility on the frozen JAR-EXP-0020 synthetic context-shift problem class.

The evidence does **not** establish:
- real-agent superiority;
- provider/model generalization;
- production readiness;
- external reproduction;
- zero safety risk.

## Mechanistic interpretation

The preceding studies progressively removed alternative explanations:

```text
0015: full VERGE on static search        -> unsupported
0016: context-conditioned repertoire     -> primary CI crossed zero
0017: post-hoc uncertainty filter        -> refuted
0018: full robust evaluation in search   -> too expensive
0019: selective robust promotion         -> weak / inconclusive
0020: margin-aware ranking               -> preregistered held-out support
```

JAR-EXP-0020 changes ranking only. Candidate proposals, evaluations, seeds, operators and search budgets are shared with the comparator.

That isolates the current supported mechanism more cleanly than the earlier studies.

## Next evidence requirement

The next research step should test transfer outside this synthetic evaluator.

Priority order:

1. independent implementation/reproduction of the Headroom ranking rule;
2. replay on held-out real execution traces where outcome/evidence labels are already fixed;
3. then a separately authorized live-agent/provider study.

Paid/live-provider execution is not implied by this result and requires its own authority/budget decision.
