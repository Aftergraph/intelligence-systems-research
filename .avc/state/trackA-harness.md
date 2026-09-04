# Track A Harness State

## Overview
Fault-injection harness + runner skeleton for STUDY-008-LIVE-v2 preregistration (approved 2026-09-04).

## Implementation Status

### Files Created

| File | Description |
|------|-------------|
| `experiments/live_benchmark/fault_injection.py` | Deterministic fault injector with 4 core fault codes |
| `experiments/live_benchmark/run_study_008v2.py` | Extended STUDY-011 runner with fault injection support |
| `tests/test_study008_v2_harness.py` | Unit tests (21 tests, all passing) |

### Fault Codes Implemented

| Code | Description | Test Status |
|------|-------------|-------------|
| FAIL-NET | 429/5xx simulation | ✅ PASSED |
| FAIL-LATENCY | Latency spike injection (>10s) | ✅ PASSED |
| FAIL-MALFORMED | Corrupt JSON response | ✅ PASSED |
| FAIL-MID-MISSION | Mid-run crash + checkpoint resume | ✅ PASSED |

### Metrics Tracked

- **VSR** (Verified Success Rate): ≥70% target
- **FCR** (False Completion Rate): ≤5% target
- **UAR** (Unauthorized Action Rate): 0 target

## Tests (21/21 passing)

- **TestFaultInjection** (8 tests): Each fault code produces intended observable
- **TestUARAccounting** (3 tests): UAR accounting prevents unauthorized actions
- **TestCheckpointResume** (3 tests): Recovery after FAIL-MID-MISSION
- **TestVerification** (3 tests): VSR/FCR computation and thresholds

## Dry-Run Verification

```
Starting STUDY-008-v2 with 20 workloads (mode=DRY_RUN)
Fault schedules: ['FAIL-NET', 'FAIL-LATENCY', 'FAIL-MALFORMED', 'FAIL-MID-MISSION']
Metrics: VSR=0.00%, FCR=0.00%, UAR=0.00%
```

## Next Steps (Pending Owner Approval)

1. Extend STUDY-008 prereg workload manifest (`data/study008_v2_workload_manifest.json`)
2. Wire live provider calls (currently SIMULATION_ONLY/DRY_RUN)
3. Add STUDY-011 verify_candidate_completion integration
4. Commit frozen protocol artifacts to main

## Protocol Reference

- Preregistration: `STUDY-008-LIVE-v2-PREREGISTRATION.md`
- STUDY-011 runner pattern: `experiments/live_benchmark/run_study_011.py`
- Frozen workloads: `data/study011_workloads_frozen.json`
