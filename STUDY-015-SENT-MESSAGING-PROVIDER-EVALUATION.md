# STUDY-015 — Sent Messaging Provider Evaluation for Aftergraph

**Experiment ID:** JAR-EXP-0014  
**Status:** PREREGISTERED / NOT YET LIVE  
**Owner:** Aftergraph Intelligence Systems Research  
**Implementation under test:** Aftergraph Runtime communications adapter  
**Provider candidate:** Sent.dm

## Research question

Does Sent improve verified transactional messaging outcomes for Aftergraph without weakening authority, idempotency, evidence quality, recovery, or cost efficiency?

This study evaluates Sent as a provider implementation. It does not redefine Aftergraph's canonical communication capability or move authority/evidence ownership into the provider.

## Canonical Aftergraph boundary

```text
intent / mission
    -> AIE authority semantics
    -> Trust Gateway enforcement / secret access
    -> Aftergraph Runtime communications.message.send
    -> provider adapter (Sent treatment / existing provider control)
    -> external transport
    -> provider read-back or signed webhook
    -> WORKS evidence
    -> independent verification
```

Sent is replaceable. The stable semantic capability is:

```text
communications.message.send
```

## Hypotheses

H1: Sent improves Verified Delivery Rate by at least 5 percentage points versus the selected baseline provider/configuration.

H2: Sent reduces Cost Per Verified Delivery by at least 20%.

H3: Sent reduces integration/operations burden by at least 30%.

At least one benefit hypothesis must pass, while every safety gate below remains green.

## Hard safety gates

Promotion is forbidden if any treatment observation contains:

- authority widening;
- duplicate external side effect caused by retry;
- acceptance of unsigned or stale webhook evidence;
- false delivery claim (`accepted/queued` treated as delivered);
- evidence correlated to the wrong provider message;
- silent resend after an indeterminate timeout.

## Study stages

### Stage 0 — contract validation

No provider network traffic.

Verify:

- `202/QUEUED != delivered`;
- deterministic action-scoped idempotency;
- authority expiry fails before network I/O;
- provider remains implementation detail;
- SMS, WhatsApp and RCS are semantic channels; `sent` is not;
- signed webhook verification rejects tampering and replay;
- provider-message correlation and dedupe work.

### Stage 1 — real provider sandbox

Requires a valid Sent credential provided at runtime.

Acceptance:

- provider authenticates request;
- request uses sandbox mode;
- HTTP 202;
- sandbox attestation header present;
- response is recorded only as `accepted_unverified`;
- no sandbox identifier is misrepresented as real delivery evidence.

Sandbox success proves API compatibility only. It does not prove carrier delivery, routing, reachability, latency, fallback, or production economics.

### Stage 2 — controlled live canary

Use owned/consented recipients only.

Each canary must have:

- explicit purpose-bound authority;
- exact recipient allowlist;
- exactly one mutation POST;
- deterministic idempotency key;
- no automatic resend on ambiguous timeout;
- bounded read-back and/or signed webhook evidence;
- terminal result captured as delivered / failed / filtered / blocked / indeterminate.

First-contact treatment should use an approved provider template unless an open conversation window is intentionally part of the test.

### Stage 3 — controlled comparison

Run matched transactional workloads.

Example workloads:

- booking confirmation;
- arrival/on-the-way notice;
- schedule change;
- service completion notice;
- payment instruction/reminder.

Control and treatment must use the same message intent, recipient eligibility, timing window and verification definition.

## Metrics

Primary:

- Verified Delivery Rate (VDR)
- Time to Verified Delivery (TVD)
- False Delivery Claim Rate (FDCR)
- Duplicate Side-Effect Rate (DSR)
- Cost Per Verified Delivery (CPVD)

Secondary:

- fallback recovery rate;
- human interventions / 100 attempts;
- integration LOC;
- provider-specific operational incidents;
- provider-selected channel distribution;
- blocked / filtered rate.

Do not collapse these into one synthetic score.

## Promotion rule

All hard safety gates must pass.

Additionally, at least one must be observed:

- VDR improvement >= 5 percentage points; or
- CPVD reduction >= 20%; or
- integration/operations burden reduction >= 30%.

A positive sandbox or architecture test alone is not promotion evidence.

## Falsification criteria

The provider hypothesis is rejected or held if:

- no measurable benefit passes;
- treatment worsens VDR materially;
- costs rise without compensating verified outcome improvement;
- duplicate effects occur;
- evidence integrity cannot be maintained;
- provider-specific complexity leaks into the semantic capability layer;
- rollback to another provider cannot be performed without changing mission/business logic.

## Evidence levels

```text
contract tests          -> architecture compatibility evidence
sandbox                 -> API compatibility evidence
live canary             -> provider execution evidence
matched comparison      -> improvement evidence
production pilot        -> operational generalization evidence
```

Claims must state their evidence level explicitly.

## Current preregistered state

At freeze time:

- canonical implementation target: `Aftergraph/runtime`;
- canonical research owner: `Aftergraph/intelligence-systems-research`;
- Rendetalje may be used as a reference tenant, but does not own the provider adapter;
- legacy transition repository `Aftergraph/autonomous-venture-company` is not an authority source for this study;
- no live Sent credential or carrier-delivery result is recorded in this study.

No production provider cutover is authorized by this document.
