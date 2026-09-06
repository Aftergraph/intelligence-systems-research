# Research Papers

This directory contains the public paper series for the Jonas Abde Intelligence Systems Research Program.

> **Current evidence rule:** manuscript labels such as `PUBLICATION-READY` describe document readiness, not submission status or external validation. The repository-level evidence audit and STUDY-011 integrity gates remain authoritative for public empirical claims.

## Start here

| Paper | Focus | Best for |
|---|---|---|
| [`01-FROM-MODELS-TO-MISSIONS-INTELLIGENCE-SYSTEMS-CONTRACT.md`](01-FROM-MODELS-TO-MISSIONS-INTELLIGENCE-SYSTEMS-CONTRACT.md) | Mission Contract / SPEC-001, evidence-gated completion, system model | Systems researchers, standards reviewers, agent-runtime implementers |
| [`02-MISSION-BENCH-EMPIRICAL-ABLATION-STUDY.md`](02-MISSION-BENCH-EMPIRICAL-ABLATION-STUDY.md) | MISSION-Bench, fault injection, ablation, verification and recovery | Benchmark and evaluation researchers |
| [`03-FORMAL-VERIFICATION-AND-AUTHORITY-ATTENUATION.md`](03-FORMAL-VERIFICATION-AND-AUTHORITY-ATTENUATION.md) | Authority attenuation, assurance boundaries and formal invariants | Security, IAM and formal-systems reviewers |
| [`04-PROGRESSIVE-DISCLOSURE-AND-CONTROL-PLANE-ECONOMICS.md`](04-PROGRESSIVE-DISCLOSURE-AND-CONTROL-PLANE-ECONOMICS.md) | Control-plane tax, CPVO and progressive disclosure | Systems economics and efficiency researchers |
| [`04-ATTENUATED-AUTHORITY-AND-EVIDENCE-GATED-SYSTEMS-ARCHITECTURE.md`](04-ATTENUATED-AUTHORITY-AND-EVIDENCE-GATED-SYSTEMS-ARCHITECTURE.md) | Heterogeneous systems architecture, evidence gates and delegated authority | Architecture and standards audiences |

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
