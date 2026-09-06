# JAR-EXP-0013 — Agent Runtime Acceleration

**State:** LIVE HOST BRIDGE READY FOR SELF-HOSTED RUNNER  
**Performance verdicts:** INCONCLUSIVE — no controlled-host confirmatory data collected yet.

## Implemented harness

The research branch contains the frozen A/B/C/D protocol, source-pin manifest, append-only SHA-256 evidence contract, deterministic trace replay, ToolRush treatment gate, browser fixture/conformance harness, verifier-authoritative mission runner, seeded factorial scheduler, bootstrap/Wilson analysis helpers, immutable promotion-gate evaluator, controlled-host preflight and Windows/Linux CI.

## Live host bridge

The bridge now adds:

- explicit argv execution with `shell=False`;
- fail-closed ToolRush and Obscura revision validation;
- ToolRush read-only doctor smoke wiring;
- Obscura executable/version validation and loopback-only CDP serve command;
- protocol-owned preflight limits frozen in revision 2;
- secret-minimized machine-readable probe evidence;
- a manual self-hosted GitHub Actions workflow restricted to `[self-hosted, Windows, X64, aftergraph-jar-exp-0013]`.

The controlled-host workflow cannot become authoritative evidence until the real Windows Hermes machine is registered with the dedicated runner label and the probe returns `READY` on that machine.

## Scientific boundary

No microbenchmark, browser, mission, or production performance result is claimed by this readiness state. `G-TR`, `G-OB`, and `G-COMB` remain `INCONCLUSIVE` until the preregistered controlled-host evidence exists. Production WORKS, Trust Gateway, AIE and governance remain unchanged.

## Next execution stage

1. Register the real controlled Windows Hermes machine as the dedicated self-hosted runner.
2. Set repository variable `JAR_EXP_0013_HOST_CONFIG` to the machine-local path configuration.
3. Run the manual `JAR-EXP-0013 controlled host` workflow and require `READY`.
4. Execute trace replay, tool microbenchmarks, browser conformance/microbenchmarks and verifier-backed A/B/C/D missions.
5. Preserve all raw evidence and evaluate G-TR, G-OB and G-COMB only after the confirmatory floors are satisfied.
