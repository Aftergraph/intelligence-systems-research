# JAR-EXP-0016 — Development Results v0.3

**Phase:** DEVELOPMENT ONLY  
**Evidence class:** EXPLORATORY_DEVELOPMENT  
**Held-out evaluated:** NO  
**Context manifest:** `88dbb5c7292de29ed4029bd565864b77e7e8fafa8b4c3488a3fab1e901e21069`  
**Raw record:** `data/verge_repertoire_dev_v0_3.json`  
**Raw SHA-256:** `a8562c5c4ed6869be0d8319b94b8bdeefc343965242427215471580c489b82b0`

## Design

- 30 search seeds.
- 6 TRAIN contexts.
- 3 DEVELOPMENT contexts.
- 12 policies per generation.
- 6 generations.
- Matched policy-context search budgets for R1, R3, R5, and R6.
- HELD_OUT contexts were not evaluated by the pilot.
- No network/provider/model calls.
- No production mutation.

## Primary development result

### Repertoire core versus global evolved policy

Fixed-operator context-conditioned repertoire minus global evolved single policy:

- seed-level paired mean delta: **+0.20626 utility**
- seed-level bootstrap 95% CI: **[+0.19145, +0.22038]**
- seed wins/ties/losses: **30 / 0 / 0**
- observed safety failures: **0 / 0** for both compared conditions

This is strong development evidence that the **context-conditioned repertoire mechanism** matters on this synthetic context-shift problem class.

It is not confirmatory evidence and does not establish external validity.

### Repertoire core versus matched random-search repertoire

Fixed-operator repertoire minus matched-budget random repertoire:

- seed-level paired mean delta: **+0.15146 utility**
- seed-level bootstrap 95% CI: **[+0.02556, +0.38264]**
- seed wins/ties/losses: **23 / 0 / 7**

This suggests the development effect is not explained only by storing one policy per context; evolutionary search contributes on the current DEVELOPMENT split.

### Adaptive operators versus fixed operators

Adaptive VERGE repertoire minus fixed-operator repertoire:

- seed-level paired mean delta: **+0.00037 utility**
- seed-level bootstrap 95% CI: **[-0.01656, +0.01700]**
- seed wins/ties/losses: **14 / 0 / 16**

The adaptive-operator mechanism is therefore **NOT SUPPORTED** by DEVELOPMENT evidence.

It must not be presented as an established contributor.

## Interpretation

JAR-EXP-0015 falsified the broad claim that the full VERGE mechanism was better on a static single-policy search problem.

JAR-EXP-0016 DEVELOPMENT now isolates a narrower signal:

```text
context-conditioned repertoire
    > one global evolved policy

evolutionary repertoire search
    > matched random repertoire

adaptive operator control
    ~= fixed operator control
```

The current evidence therefore supports simplifying the candidate mechanism before any held-out evaluation.

## Development decision

Freeze the confirmatory candidate as **VERGE Repertoire Core**:

- context-conditioned feasible archive;
- nearest-context retrieval;
- fixed, declared variation operator distribution;
- hard evidence/authority feasibility gates;
- no adaptive operator-credit requirement.

Retain adaptive operator selection as a secondary experimental arm only.

This is a DEVELOPMENT-driven model-selection decision and is recorded before any held-out evaluation.

## Limits

The current held-out contexts are structurally excluded from evaluation, but their definitions exist in the repository and are therefore not human-blind.

A positive held-out result would remain internal synthetic evidence, not independent reproduction.

No real-agent, provider, or production superiority claim is permitted from this study.
