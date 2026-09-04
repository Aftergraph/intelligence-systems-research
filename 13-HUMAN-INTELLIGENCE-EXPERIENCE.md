# Human–Intelligence Experience

## Core UX principle
Machine-first internals. Human-first surface.

Users should not need to understand:
MCP, A2A, YAML, policy engines, authority graphs or trajectory schemas.

## Primary interaction primitive
Delegation, not chat.

### Delegation continuum
- L0 Direct
- L1 Assist
- L2 Collaborate
- L3 Delegate bounded task
- L4 Delegate mission
- L5 Autonomous until exception

The level must be changeable during execution.

## Core human actions
Ask, Instruct, Delegate, Review, Approve, Take over, Verify, Pause, Cancel, Resume.

## Core surfaces
- NOW
- Mission
- Needs You
- Trajectory
- Evidence
- Control

Chat/voice/CLI/IDE/mobile/API are interaction surfaces over the same mission state.

## Goal-first onboarding
Default first question:
“What do you want to accomplish?”

Do not start with framework/model/MCP setup.

## Progressive disclosure
Default:
goal, progress, needs-you, outcome.

Expanded:
plan, agents, cost, authority.

Expert:
trajectory, policies, evidence, telemetry.

Developer:
schemas, protocols, adapters, manifests.

## Risk-adaptive friction
Low risk:
execute quietly → report outcome.

Medium risk:
execute → show progress → verify.

High risk:
preview → explain impact → approve → execute → verify.

Friction should roughly increase with risk.

## Explainability
Do not expose raw hidden reasoning.
Expose:
decision, rationale, relevant evidence, constraints and alternatives.

## Failure UX
Never force users to restart if state can be recovered.
Show:
what completed, what failed, why, what remains safe, next options.

## Retention philosophy
Optimize recurring useful outcomes, not session length.

Candidate North Star:
**Weekly Verified Outcomes per Active User (WVOU)**

Secondary:
**Human Effort per Verified Outcome (HEVO)**

## Trust
Do not maximize trust.
Optimize appropriate reliance / trust calibration.

Metrics:
Overtrust Rate, Undertrust Rate, State Comprehension, Takeover Success, Time to Understand Failure.
