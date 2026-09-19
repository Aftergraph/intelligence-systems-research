# JAR-EXP-0016 — Development Results v0.5

**Phase:** DEVELOPMENT ONLY  
**Evidence class:** EXPLORATORY_DEVELOPMENT  
**Held-out evaluated:** NO  
**Context manifest:** `88dbb5c7292de29ed4029bd565864b77e7e8fafa8b4c3488a3fab1e901e21069`  
**Raw record:** `data/verge_repertoire_dev_v0_5.json`  
**Raw SHA-256:** `87ece9bc6ff9d3e07c38aab92d8156fa84117e1c21caca5e5ba6725c7720c15a`

## Design

- 30 search seeds.
- 6 TRAIN contexts.
- 3 DEVELOPMENT contexts.
- 12 policies per generation.
- 6 generations.
- Matched policy-context search budgets for R1, R3, R4, R5, and R6.
- HELD_OUT contexts were not evaluated by the pilot.
- No network/provider/model calls.
- No production mutation.

## Repertoire core versus non-repertoire baselines

### R5-C core versus R1 global evolved

Fixed-operator context-conditioned repertoire minus global evolved single policy:

- seed-level paired mean delta: **+0.20626 utility**
- seed-level bootstrap 95% CI: **[+0.19145, +0.22038]**
- seed wins/ties/losses: **30 / 0 / 0**
- observed safety failures: **0 / 0**

### R4 global Pareto comparator

R4 global Pareto and R1 global scalar evolution produced the same DEVELOPMENT mean utility:

```text
R1-global-evolved mean utility: 102.96145847200175
R4-global-pareto  mean utility: 102.96145847200175
```

The repertoire development delta versus R4 is therefore the same as versus R1:

```text
+0.2066256246341319
```

Because R1 and R4 are tied on DEVELOPMENT, R1 is selected as the primary non-repertoire comparator by parsimony. R4 remains a reported secondary comparator.

## Repertoire core versus matched random repertoire

Fixed-operator repertoire minus matched-budget random repertoire:

- seed-level paired mean delta: **+0.15146 utility**
- seed-level bootstrap 95% CI: **[+0.02556, +0.38264]**
- seed wins/ties/losses: **23 / 0 / 7**

This suggests the development effect is not explained only by storing one policy per context; evolutionary search contributes on the current DEVELOPMENT split.

## Adaptive operators versus fixed operators

Adaptive VERGE repertoire minus fixed-operator repertoire:

- seed-level paired mean delta: **+0.00037 utility**
- seed-level bootstrap 95% CI: **[-0.01656, +0.01700]**
- seed wins/ties/losses: **14 / 0 / 16**

Adaptive operator credit is therefore **NOT SUPPORTED** as a contributor by DEVELOPMENT evidence.

## Safety hostile-review result

A later pre-held-out review found that source-context feasibility did not imply target-context feasibility.

The selector was changed to:

```text
source elite
→ target-context feasibility check
→ discard infeasible
→ nearest-context ranking among feasible candidates
→ fail closed if none remain
```

Two tests failed before the fix and passed after it.

The 30-seed DEVELOPMENT evidence was then rerun. The resulting serialized output was byte-identical to the previous v0.3 result, proving that the safety gate did not alter the recorded DEVELOPMENT outcomes.

## Development conclusion

The evidence supports carrying forward the **repertoire mechanism**, not the adaptive-operator mechanism:

```text
context-conditioned evolutionary repertoire
    > global single policy

evolutionary repertoire
    > matched random repertoire

adaptive operator control
    ~= fixed operator control
```

The held-out primary candidate is therefore frozen as **VERGE Repertoire Core (R5-C)** with fixed operators and target-context fail-closed feasibility.

## Limits

The HELD_OUT definitions exist in the repository and are structurally excluded from tuning/evaluation, but they are not human-blind.

A positive held-out result can support only an internal deterministic claim on this frozen synthetic problem class. It cannot establish real-agent or production superiority.
