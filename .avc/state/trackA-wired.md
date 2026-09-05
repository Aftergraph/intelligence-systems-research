# Track A Status: STUDY-008-v2 Runner Wired

## Commit
c578133 - STUDY-008-v2 runner: provider matrix + 8-cell wiring + fault schedules (DRY_RUN verified)

## Status
**READY FOR OWNER APPROVAL**

## Completed
- [x] Provider model matrix (`data/study008_v2_provider_model_matrix.json`)
  - 2 providers: dialagram, openrouter
  - 5 models total (3 dialagram, 2 openrouter)
- [x] 8-cell matrix wired (2 providers × 4 conditions: A/C/F/G)
- [x] Fault schedule integration (4 fault codes)
- [x] DRY_RUN verified: all 8 cells exercised
- [x] Tests pass: 22/22 (including new test_provider_cells_matrix)
- [x] Real API path ready (from run_study_011.py)

## Remaining
- [ ] Owner approval for provider keys
- [ ] Phase 2 provider access (openai, anthropic, google)
- [ ] Full workload set (25 benchmark tasks)

## Metrics Target
- VSR ≥ 70%
- FCR ≤ 5%
- UAR = 0
- Attempt ceiling: 619
