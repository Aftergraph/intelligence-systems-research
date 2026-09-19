# JAR-EXP-0017 — DEVELOPMENT Results v0.1

**Phase:** DEVELOPMENT ONLY  
**Evidence class:** EXPLORATORY_DEVELOPMENT  
**Held-out evaluated:** NO  
**Context manifest:** `3e6fe4440172a8244d41a01ad1e944bd21fbdc27090230a0b7c8a769622c744d`  
**Raw record:** `data/verge_halo_dev_v0_1.json`  
**Raw SHA-256:** `c42c96f58d1772604ab34920c592d5818c8174e9a3eb107803aaafdd4559248a`

## Design

- 30 search seeds.
- 8 TRAIN contexts.
- 4 DEVELOPMENT contexts.
- population size 12.
- 6 generations.
- One fixed-operator repertoire evolved per seed.
- NOMINAL and HALO selectors reuse the exact same repertoire.
- No HELD_OUT context was evaluated.
- No network/model/provider calls.
- No production mutation.

## Primary DEVELOPMENT endpoint

Per seed:

```text
DeltaWorst =
  min DEVELOPMENT utility under HALO
  -
  min DEVELOPMENT utility under NOMINAL
```

Observed:

```text
mean DeltaWorst = +1.317654680410071
95% paired bootstrap CI = [+0.32868245381295985,
                            +2.626864956240069]

HALO wins / ties / losses = 11 / 18 / 1
```

The DEVELOPMENT interval is positive.

This is exploratory mechanism-selection evidence only.

## Safety

Across 120 DEVELOPMENT context evaluations per selector:

```text
HALO:
  verified              120 / 120
  false completion        0
  unauthorized actions    0
  evidence failures       0
  selection failures      0
  human interventions     0

NOMINAL:
  verified              120 / 120
  false completion        0
  unauthorized actions    0
  evidence failures       0
  selection failures      0
  human interventions     4
```

## Mean utility / cost / latency

```text
HALO
  mean utility       102.92131249042298
  cost               333.0881
  CPVO                 2.7757341666666666
  latency            198.3585645969692

NOMINAL
  mean utility       102.59239078092678
  cost               330.2479000000001
  CPVO                 2.752065833333334
  latency            203.0574651551452
```

HALO improves mean DEVELOPMENT utility and aggregate latency while paying a small direct cost increase.

## Selector evaluation overhead

```text
HALO selector evaluations     11,520
NOMINAL selector evaluations     960
```

The 12x selector-evaluation overhead is expected from the frozen 12-point uncertainty halo and must remain visible in later interpretation.

## Context-level mean utility deltas

```text
DEV-HALO-BALANCED  +0.32431
DEV-HALO-LATENCY   +0.31826
DEV-HALO-RECOVERY  +0.67441
DEV-HALO-RISK      -0.00130
```

The DEVELOPMENT benefit is not uniform across context families.

## Mechanism decision

The DEVELOPMENT result is sufficient to carry the already-specified Halo selector forward to a frozen internal HELD_OUT test.

No mechanism tuning is authorized after this point.

## Claim boundary

Admissible:

> DEVELOPMENT evidence supports testing robust uncertainty-halo selection on a new held-out synthetic context split.

Not admissible:

- VERGE Halo is superior.
- H1-HALO is proven.
- Halo generalizes to real agents.
- Halo is production ready.
