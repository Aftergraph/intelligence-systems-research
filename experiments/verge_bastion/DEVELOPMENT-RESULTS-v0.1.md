# JAR-EXP-0018 — DEVELOPMENT Result v0.1

**Phase:** DEVELOPMENT ONLY  
**Evidence class:** EXPLORATORY_DEVELOPMENT  
**HELD_OUT evaluated:** NO  
**Raw record:** `data/verge_bastion_dev_v0_1.json`  
**Raw SHA-256:** `9af09305c6df97dec036f9183e9d50ac8e57acbbd08ab96399cb50ce81cca327`

## Frozen development setup

- 30 seeds.
- 8 TRAIN contexts.
- 4 DEVELOPMENT contexts.
- population size 8.
- 256 policy-context evaluations per TRAIN niche per arm.
- total search budget per seed:
  - NOMINAL: 2048 policy-context evaluations
  - BASTION: 2048 policy-context evaluations
- HELD_OUT contexts were not evaluated.

## Primary development endpoint

```text
mean DeltaWorst(Bastion - Nominal)
  = -1.7721274649347207

95% paired bootstrap CI
  = [-4.002585613536676,
     +0.4384935464538264]

wins / ties / losses
  = 6 / 2 / 22
```

The preregistered development candidate does not show a positive signal.

## Robust coverage

```text
BASTION TRAIN robust coverage = 1.0
NOMINAL TRAIN robust coverage = 1.0
```

This is important: the extra halo-aware search pressure did not improve TRAIN robust-feasibility coverage because the nominal search already retained robustly feasible elites in all TRAIN niches.

## Search-efficiency cost

Matched total policy-context budget implies:

```text
NOMINAL candidate proposals / seed = 2048
BASTION candidate proposals / seed = 256
```

Bastion spends 8 context evaluations per candidate and therefore explores only one eighth as many genomes.

The robust search signal is consequently competing against a very large exploration penalty.

## Development context deltas

```text
DEV-BAS-BAL   +0.19084 mean utility
DEV-BAS-LAT   +1.09874
DEV-BAS-REC   +0.53538
DEV-BAS-RISK  -4.07487
```

The negative primary result is dominated by the risk context, while the other three context families show positive mean deltas.

## Scientific conclusion

JAR-EXP-0018 does **not** justify HELD_OUT execution.

The current robust-evolution design is inefficient under a fair total policy-context budget:

```text
evaluate every candidate on full halo
→ 8x fewer candidate proposals
→ lower exploration depth
→ no TRAIN coverage gain
→ worse DEVELOPMENT worst-context utility
```

The correct response is not to loosen the frozen budget or inspect HELD_OUT.

The mechanism should be retired at DEVELOPMENT.

## Next research implication

The next defensible mechanism should preserve broad nominal exploration and spend expensive robust halo evaluations only on a promoted subset of candidates.

Conceptually:

```text
many cheap nominal proposals
→ promotion gate
→ expensive robust evaluation on elites/uncertain candidates
→ robust archive
```

This is a new algorithm and requires a new experiment ID.

## Claim boundary

Admissible:

> Full-halo evaluation of every candidate is too evaluation-expensive to beat nominal search under the matched JAR-EXP-0018 development budget.

Not admissible:

- robust evolution is generally inferior;
- robustness is unnecessary;
- JAR-EXP-0018 says anything about HELD_OUT;
- the result generalizes to live agents.
