# Intelligence Systems Research Public Release Gate

**Program:** Jonas Abde Intelligence Systems Research Program  
**Public maturity:** Level C+ / Provisional-D where the repository audit currently supports it  
**Authoritative sources:** repository README, evidence audit, claim registry, experiment registry, STUDY-011 integrity artifacts

This gate prevents publication copy, release titles, and social posts from silently becoming stronger than the underlying evidence.

## Release classes

### Research Snapshot

Use for a coherent public research revision whose claims remain bounded to existing in-tree evidence.

Suggested title:

`SPEC-001 Mission Contract v0.1 — Research snapshot`

### Benchmark Snapshot

Use for MISSION-Bench or another dataset/harness release where the exact workload, code, seeds/configuration and evidence class are frozen.

Suggested title:

`MISSION-Bench — deterministic benchmark snapshot`

### Live Confirmatory Result

Use only after the preregistered integrity gate admits the relevant live-provider result into the canonical evidence/claim registries.

A run finishing is not sufficient. A log line is not sufficient. A persuasive graph is particularly not sufficient.

### Independent Reproduction

Use only for work performed by an actually independent implementation/team under a documented reproduction protocol. Internal clean-room paths do not automatically satisfy this label.

## Mandatory pre-release checks

- [ ] exact release commit recorded
- [ ] `pytest` / repository verification suite rerun on exact release head where applicable
- [ ] conformance result regenerated when the release references conformance
- [ ] claim registry reviewed
- [ ] claim-evidence audit reviewed
- [ ] experiment registry reviewed
- [ ] manuscript labels checked against current audited status
- [ ] deterministic/simulated/live/independent evidence classes explicitly separated
- [ ] confidence intervals and sample bounds retained for zero-observed-failure claims
- [ ] `CITATION.cff` reviewed
- [ ] reproduction commands and dependencies documented
- [ ] raw results and analysis scripts referenced
- [ ] AI-assistance disclosure retained where applicable
- [ ] patent/IP disclosure gate checked before publishing potentially novel mechanisms

## Metrics-heavy publication rule

A public post may quote a numerical result only when it can identify:

1. the experiment/study ID;
2. the evidence class;
3. the sample size or applicable denominator;
4. the canonical source artifact;
5. the exact repository revision or release.

Where the repository audit has reclassified or walked back a historical number, the audited value wins.

## STUDY-011 rule

Before any post that uses STUDY-011 as live-confirmatory evidence:

- inspect `STUDY-011-READINESS-REPORT.md`;
- inspect `STUDY-011-AMENDMENTS.md` and the preregistration manifest;
- inspect the current experiment and claim registries;
- verify that the claimed result has passed the confirmatory integrity gate;
- distinguish execution progress from admitted confirmatory evidence.

## External criticism target

Every flagship research release should invite at least one falsifiable response:

- reproduce a result;
- implement SPEC-001 independently;
- provide contradictory prior art;
- attack an authority/evidence invariant;
- show that a simpler conventional-agent baseline matches the system at lower cost/complexity.

If the research cannot survive a hostile reader with the source code open, prettier launch copy will not rescue it.
