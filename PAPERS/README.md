# Research Papers

This directory contains the public paper series for the Jonas Abde Intelligence Systems Research Program.

> **Current evidence rule:** manuscript labels such as `PUBLICATION-READY` describe document readiness, not submission status or external validation. The repository-level evidence audit and STUDY-011 integrity gates remain authoritative for public empirical claims.

## Start here

| Paper | Focus | Evidence status | Best for |
|---|---|---|---|
| [`01-FROM-MODELS-TO-MISSIONS-INTELLIGENCE-SYSTEMS-CONTRACT.md`](01-FROM-MODELS-TO-MISSIONS-INTELLIGENCE-SYSTEMS-CONTRACT.md) | Mission Contract / SPEC-001, evidence-gated completion, system model | Complete program synthesis; simulation/conformance claims remain bounded by repository evidence gates | Systems researchers, standards reviewers, agent-runtime implementers |
| [`02-MISSION-BENCH-ABLATION-AND-EMPIRICAL-EVALUATION.md`](02-MISSION-BENCH-ABLATION-AND-EMPIRICAL-EVALUATION.md) | MISSION-Bench, fault injection, ablation, verification and recovery | Publication-ready manuscript; not external validation | Benchmark and evaluation researchers |
| [`03-THE-ECONOMICS-OF-VERIFIED-INTELLIGENT-SYSTEMS.md`](03-THE-ECONOMICS-OF-VERIFIED-INTELLIGENT-SYSTEMS.md) | Control-plane tax, CPVO and amortized recovery economics | Publication-ready manuscript; not external validation | Systems economics and efficiency researchers |
| [`04-ATTENUATED-AUTHORITY-AND-EVIDENCE-GATED-SYSTEMS-ARCHITECTURE.md`](04-ATTENUATED-AUTHORITY-AND-EVIDENCE-GATED-SYSTEMS-ARCHITECTURE.md) | Heterogeneous systems architecture, causal trajectories, evidence gates and delegated authority | Publication-ready architectural specification; not external validation | Architecture, security and standards audiences |
| [`05-FRONTIER-AGENT-BREAKOUT-AND-INSTITUTIONAL-CONTROL.md`](05-FRONTIER-AGENT-BREAKOUT-AND-INSTITUTIONAL-CONTROL.md) | 2026 frontier-agent incidents, institutional control, containment taxonomy, proposed ICT benchmark | Public working paper; STUDY-012 is the active empirical follow-on | Agent-security, frontier-safety, governance and systems researchers |


## Publication exports

Reader-ready PDF and editable DOCX builds for Papers 01–05 are published under [`exports/`](exports/). These are convenience renderings; the numbered Markdown manuscripts above remain the canonical text sources.

## Additional working papers

Research manuscripts that are part of the broader Aftergraph program but are **not** numbered members of the 01–05 series live under [`additional/`](additional/):

- [`Autonomous Work Detection`](additional/awd/AUTONOMOUS-WORK-DETECTION.md) — working paper / product research protocol; proposal and hypothesis-generating status.
- [`After Graph / The Institution Layer`](additional/institution-layer/README.md) — current v4 research/standards manuscript, retained as a supplemental research track rather than silently promoted into the numbered series.

## Core research thesis

The program investigates whether long-horizon autonomous systems need a vendor-neutral systems contract that connects:

```text
human intent
→ mission
→ state
→ capabilities
→ authority
→ budgets/resources
→ execution
→ trajectory
→ assurance
→ evidence
→ verified outcome
→ recovery/adaptation
```

The central normative distinction is:

> **Declared completion is not verified completion.**

SPEC-001 formalizes the system as `IS = ⟨M,S,C,A,B,T,E,V⟩` and separates stochastic execution from independent verification authority.

## Evidence classes

When reading or citing results, keep these classes separate:

1. **Deterministic / sandbox testbed evidence**
2. **Simulation or cognitive-model evidence**
3. **Live-provider methodological pilots**
4. **Live confirmatory evidence admitted through the preregistered gate**
5. **Conformance evidence**
6. **Independent external reproduction**

A result in one class does not silently upgrade into another. The repository README, evidence audit, experiment registry and claim registry are the current sources of truth.

## Reproduce before repeating

Useful commands from the repository root:

```bash
pytest -v
python conformance/runner.py
python validation/cross_domain_validation.py
python cli/mission_cli.py audit
```

For exact reproduction, pin the commit or release you used and record model/provider/version, environment, parameters, datasets, seeds and raw outputs.

## Citation

Use [`../CITATION.cff`](../CITATION.cff) and include the exact commit or release. If citing one paper specifically, cite the paper title as well as the repository revision that supplied its evidence and artifacts.

## Review and falsification

Particularly useful external contributions include:

- independent implementations of SPEC-001;
- failed conformance vectors;
- contradictory prior art;
- independent replication of benchmark results;
- adversarial attacks on evidence or authority boundaries;
- evidence that a simpler conventional-agent baseline matches the full system.

The program explicitly permits rejection or narrowing of the broader systems-contract hypothesis if a stronger, simpler baseline wins. Research gets considerably less embarrassing when it is allowed to lose.
