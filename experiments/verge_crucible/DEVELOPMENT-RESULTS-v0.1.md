# JAR-EXP-0019 — DEVELOPMENT Result v0.1

**Phase:** DEVELOPMENT ONLY  
**Evidence class:** EXPLORATORY_DEVELOPMENT  
**HELD_OUT evaluated:** NO  
**Raw record:** `data/verge_crucible_dev_v0_1.json`  
**Raw SHA-256:** `86701853803ff2ab35a6dee86e724cd39c45da516c3eb2b7c98e2f05172df638`

## Frozen development setup

- 30 seeds.
- 8 TRAIN contexts.
- 4 DEVELOPMENT contexts.
- Per TRAIN niche total policy-context budget: 256.
- NOMINAL: 256 cheap nominal candidate evaluations.
- CRUCIBLE: 144 nominal candidate evaluations + 16 promoted candidates × 7 additional halo points = 256.
- HELD_OUT was not evaluated.

## Primary DEVELOPMENT endpoint

```text
mean DeltaWorst(Crucible - Nominal)
  = +0.3026299076406213

95% paired bootstrap CI
  = [-0.6639345140630544,
     +1.5394432735789905]

wins / ties / losses
  = 2 / 26 / 2
```

The frozen DEVELOPMENT gate required a positive bootstrap lower bound.

It is not positive.

Therefore JAR-EXP-0019 does **not** advance to HELD_OUT.

## Robust coverage

```text
CRUCIBLE TRAIN robust coverage = 1.0
NOMINAL TRAIN robust coverage  = 1.0
```

The multi-fidelity promotion mechanism preserved much more proposal breadth than JAR-EXP-0018, but it still did not increase robust-feasibility coverage because the nominal baseline already achieved full TRAIN robust coverage.

## Interpretation

The progression across the last two experiments is:

```text
JAR-EXP-0018
full halo on every candidate
→ too expensive
→ clear DEVELOPMENT loss

JAR-EXP-0019
cheap exploration + selective halo promotion
→ removes most exploration penalty
→ mean DeltaWorst becomes positive
→ but effect is weak / highly tied
→ bootstrap interval crosses zero
```

This is useful evidence: evaluation efficiency improved, but robust feasibility itself is no longer the limiting factor on the current TRAIN distribution.

The remaining problem is **ranking/calibration among already-feasible elites**, especially under unseen target shifts.

## Scientific verdict

Stop JAR-EXP-0019 at DEVELOPMENT.

Do not inspect HELD_OUT and do not tune the promotion fraction on the same DEVELOPMENT outcomes.

A new study should target a different mechanism, not a post-hoc parameter search over 144/16.

## Next research implication

The next defensible hypothesis should focus on **margin-aware elite ranking** rather than additional feasibility testing.

Candidate signals that can be frozen before evaluation include:

- confidence margin above context threshold;
- verification-depth margin;
- retry/recovery margin;
- cost/latency slack;
- robust utility margin across a small promoted set.

A margin-aware ranking rule can retain the same evaluation budget while distinguishing robustly feasible elites that otherwise tie on nominal verified success.

This requires a new experiment ID and new context manifest.

## Claim boundary

Admissible:

> Multi-fidelity robustness screening removed most of the evaluation-efficiency penalty seen in JAR-EXP-0018, but did not pass the frozen JAR-EXP-0019 DEVELOPMENT gate.

Not admissible:

- Crucible is superior.
- H1-C is supported.
- HELD_OUT behavior is known.
- The result generalizes to live agents.
