# Meta Muse Prior-Art Amendment — 2026-09-09

**Status:** Post-freeze research amendment. This document updates the prior-art landscape after the 2026-09-08 public Muse launch. It does not rewrite historical evidence cuts, invention records, preregistrations, or empirical results.

## Decision

Meta's Muse/Muse Code publications are now explicit prior art and a high-value architecture comparator for persistent autonomous-agent systems. They are evidence of **independent architectural convergence**, not evidence that Meta reproduced, validated, or adopted SPEC-001, AIE, MISSION-Bench, or any Aftergraph empirical result.

The research program must therefore reject novelty language that depends only on any of the following broad mechanisms:

- persistent/background autonomous agents;
- dedicated or isolated agent computers;
- long-horizon background work, schedules, or concurrent subagents;
- durable application state outside a conversational turn;
- external permission/authorization authority separated from the reasoning agent;
- scoped, expiring, revocable permissions and human approvals;
- credential isolation/brokering or surrogate-style credential handling;
- network-egress mediation;
- least-privilege connector/tool access;
- agent-authored skills/connectors as a general mechanism.

These mechanisms may still be used in Aftergraph implementations, but their existence is not a novelty claim.

## Dated sources added to `data/source_registry.csv`

### SRC-019 — Muse Code / Muse Spark 1.2

**Publication date:** 2026-08-05  
**Source:** Meta AI Research, *Introducing Muse Code and Muse Spark 1.2*  
**URI:** https://research.meta.ai/blog/introducing-muse-code-and-muse-spark-1-2

Relevant prior-art scope includes persistent asynchronous background coding agents, event-log/recovery architecture, goal/plan surfaces, and long-horizon multi-agent execution.

### SRC-020 — Muse Spark 1.3

**Publication date:** 2026-09-02  
**Source:** Meta AI Research, *Introducing Muse Spark 1.3*  
**URI:** https://research.meta.ai/blog/introducing-muse-spark-1-3

Relevant comparator scope includes long-horizon agentic workflows, multiple concurrent workflows, tool use, constraint retention, recovery behavior, and human escalation.

### SRC-021 — Muse security architecture

**Publication date:** 2026-09-08  
**Source:** Meta AI Research, *Security and Safety for AI Agents: Our Approach with Muse*  
**URI:** https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse

Relevant prior-art scope includes isolated agent execution, an external permission authority, scoped approvals, credential separation/brokering, network-egress control, durable state, and human approval boundaries.

## Narrowed candidate research boundary

The existence of Muse does **not** by itself resolve whether a gap remains at a more portable systems layer. Candidate differentiators that remain research questions include:

1. **Portable mission semantics** that survive model/runtime/vendor replacement.
2. **Portable authority and delegation semantics**, including monotonic attenuation/conservation across delegation chains.
3. **Budget inheritance/conservation** as a mission/institution primitive rather than a product-specific quota.
4. **Evidence-gated completion** in which execution completion cannot self-upgrade to independent verification.
5. **Cross-runtime conformance** for mission, authority, evidence, and lifecycle semantics.
6. **Portable settlement/quittance semantics** that connect durable execution to independently verifiable outcomes.
7. **Governed topology mutation** across heterogeneous agent graphs/institutions.

These are candidate gaps, not established novelty conclusions. Each must continue through prior-art review, falsification, conformance, independent implementation, and empirical evidence as applicable.

## Claim-language rule

Use this distinction consistently:

```text
external architectural convergence
    supports: problem relevance / market pressure / mechanism existence
    does not prove: Aftergraph metric, conformance result, novelty, or causation

independent empirical validation
    requires: valid Aftergraph experiment or external reproduction under a defined protocol
```

Accordingly:

- STUDY-008 remains `METHODOLOGICAL_PILOT` and is not re-promoted.
- The 275 attempted runs must never be described as 275 valid live executions.
- Deterministic MISSION-Bench FCR/UAR/CPVO results remain testbed results.
- STUDY-011 remains the gate for strong live cross-provider claims.
- No Muse publication upgrades AIE conformance or SPEC-001 evidence.

## Future Muse comparison

Muse is a candidate for a preregistered black-box comparison only where the public/authorized interface permits it. The protocol should freeze hypotheses and metrics before outcome inspection and should test at least:

- mission continuity across restart/state transitions;
- permission scope and revocation timing;
- authorization between plan-time and execution-time;
- context/state continuity;
- false-completion behavior against external ground truth;
- audit completeness;
- subagent authority inheritance;
- independent evidence/verification availability;
- cost/human-intervention measures where observable.

No test may attempt to bypass access controls, acquire unavailable internals, or infer implementation details that the authorized interface cannot establish.

## Falsifier for the remaining systems-layer thesis

A strong falsifier would be an existing, independently specified and interoperable system that already supplies portable mission + authority/delegation + budget + evidence-gated verification semantics across heterogeneous runtimes with independent conformance evidence. If such prior art is found, the remaining novelty boundary must narrow again or be rejected.

## Evidence discipline

This amendment changes the prior-art landscape and claim wording only. It does not alter frozen raw experiment data, preregistration manifests, historical evidence cuts, or patent/invention records. Any legal/patent conclusion requires counsel review and must not be inferred from this engineering research amendment.