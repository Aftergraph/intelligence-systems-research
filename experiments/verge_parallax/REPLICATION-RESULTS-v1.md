# JAR-EXP-0021 — Parallax Internal Replication Result v1

**Evidence class:** INTERNAL_IMPLEMENTATION_REPLICATION  
**Parent experiment:** JAR-EXP-0020  
**Raw record:** `data/verge_parallax_replication_v1.json`  
**Raw SHA-256:** `39b32f8ff53aa58f9a8a6a8cbaffd91f8beba165a767cb2ab393ae0902655b80`

## Replication restriction

The replica implementation does **not** import:

```text
experiments.verge_headroom.ranking
```

and does not call the original Headroom selector helpers.

It derives the ranking rule directly from the frozen written JAR-EXP-0020 specification while reusing shared deterministic candidate generation, genome contracts and evaluator semantics.

This is therefore a second implementation path, not an external independent reproduction.

## Exact reproduction result

```text
seed_delta_vector_exact_match = true
mean_exact_match              = true
ci_exact_match                = true
support_verdict_match         = true
```

Replica summary:

```text
mean DeltaWorst = +3.843189264168792

95% bootstrap CI
  = [+2.240316653152203,
     +5.452553729161985]

wins / ties / losses
  = 17 / 11 / 2

verified successes          = 120 / 120
unauthorized actions        = 0
evidence-integrity failures = 0
selection failures          = 0
positive_support            = true
```

The seed-level DeltaWorst vector is an exact match to the parent JAR-EXP-0020 artifact.

## Verification

Focused replication suite:

```text
3 passed in 37.55s
```

The test suite also asserts that the replica source does not import the original ranking implementation.

## Scientific interpretation

JAR-EXP-0021 removes one implementation-path concern:

> the positive JAR-EXP-0020 result is reproducible from the frozen written ranking specification through a second internal code path.

It does **not** remove:
- evaluator dependence;
- synthetic-context dependence;
- deterministic candidate-generator dependence;
- author/team dependence;
- lack of real-agent evidence;
- lack of external independent reproduction.

## Next evidence requirement

The next material step is not another synthetic ranking variant.

The supported mechanism should be tested against **fixed-label execution traces** or an independently produced candidate/outcome corpus, followed by a separately authorized live-agent/provider study.

Paid provider execution is outside this replication result and requires its own budget/authority decision.
