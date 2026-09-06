# JAR-EXP-0013 Post-Merge Main Dispatch Hotfix

## Goal
Ensure the canonical controlled-host operator entrypoint dispatches the optional self-hosted workflow from `main` after PR #5 merged, rather than retaining the retired feature-branch default.

## TDD contract
1. RED: require `start-controlled-host.ps1` to default `$Branch` to `main` and reject the retired research branch literal.
2. GREEN: change only the default branch parameter in `start-controlled-host.ps1`.
3. Verify full runtime-acceleration suite and repository PR CI.
4. Update Issue #3 with the canonical merged execution command and merge SHA.

## Scientific boundary
This hotfix changes no protocol, treatment pin, workload, metric, statistical gate, or performance evidence. It only corrects the remote workflow-dispatch ref after the research harness became canonical on `main`.
