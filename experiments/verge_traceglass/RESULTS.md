# JAR-EXP-0022 — Traceglass Evidence-Readiness Result

**Verdict:** NOT READY FOR OUT-OF-SIMULATOR HEADROOM REPLAY  
**Compatible committed records:** 0  
**Protected/provider calls made:** 0

## What was audited

Traceglass inspected the committed evidence shapes for:

- STUDY-008 `data/live_results.csv`;
- STUDY-011 pilot `run_records.jsonl`;
- durability fault-injection results;
- assurance adversarial results;
- JAR-EXP-0013 deterministic trace-replay workload and controlled-host evidence contract.

## Result

None contains the complete frozen Headroom tuple:

```text
pre-action policy:
  confidence_threshold
  verification_depth
  retry_ceiling

context requirements:
  min_confidence
  min_verification
  min_retries

fixed outcomes:
  verified success
  false completion
  unauthorized action
  evidence-integrity failure
  cost
  latency
  human interventions

immutable provenance
```

Therefore no legitimate out-of-simulator comparison can be run without reconstructing or inventing Headroom labels after observing outcomes.

That would invalidate the test.

## Source-specific findings

### STUDY-008

The committed table includes run/workload IDs, VSR/FCR-style labels, cost/latency and run classification.

However:
- the audited claim record states only **2/275** attempts were LIVE_VALID;
- most committed rows are SIMULATED;
- policy margin fields and context thresholds are absent.

**Result:** not admissible.

### STUDY-011 pilot

The pilot contains genuine `LIVE_VALID` provider records with provider request IDs, request/response hashes, final mission state and latency.

That is valuable provenance evidence.

But it lacks:
- confidence threshold;
- verification depth;
- retry ceiling;
- context minimum thresholds.

**Result:** real provider evidence, but not Headroom-compatible.

### Durability + assurance

These are internal controlled execution evidence with meaningful fixed labels, but they test different mechanisms and lack the policy/context margin tuple.

**Result:** not Headroom-compatible.

### JAR-EXP-0013

The committed trace definition is a deterministic fixture. The controlled-host runbook records real Windows-host performance promotion results and defines local raw evidence locations, but the committed trace schema itself contains operations rather than Headroom policy margins.

**Result:** useful execution evidence, wrong experimental object.

## Scientific conclusion

The next research bottleneck is now concrete:

```text
Headroom mechanism
    ✅ synthetic held-out support
    ✅ second internal implementation reproduction
    ❌ real/fixed execution corpus with pre-action margin labels
```

The correct next step is **instrumentation**, not another synthetic optimization variant.

Runtime/WORKS execution evidence needs to capture the policy configuration and context requirements *before execution*, together with verifier outcomes and immutable provenance.

Only after such records exist can Headroom be tested honestly outside the synthetic evaluator.

## Canonical ownership boundary

Traceglass does not become a production telemetry authority.

- Runtime/WORKS should own execution/work evidence semantics.
- Governance owns cross-repo contract adoption.
- ISR owns the research admission criteria and resulting experiment evidence.

JAR-EXP-0022 therefore closes as an evidence-readiness study and should hand off the missing capture contract rather than silently adding parallel production truth.
