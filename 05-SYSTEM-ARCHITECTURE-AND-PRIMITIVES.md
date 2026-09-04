# System Architecture and Primitives

## Working system tuple
IS = <Mission, State, Perception, Knowledge, Reasoning, Capabilities, Actions, Authority, Assurance, Evidence, Humans, Resources>

## Core primitives

### Mission
Bounded intended outcome with objective, constraints, authority, budget and success criteria.

### State
Not one object. At minimum distinguish:
- mission state
- world/external state
- runtime state
- agent state
- memory state

### Capability
A discoverable ability that can be provided by a tool, skill, agent, service, model or local runtime.

### Authority
Permission to perform a capability for a bounded purpose under constraints.

### Trajectory
Ordered execution record of observations, decisions, actions, state transitions and relevant metadata.

### Assurance
Umbrella for Test, Evaluation, Verification and Validation.

### Evidence
Artifact or observation supporting a specific claim.

### Verified Outcome
Outcome whose required acceptance criteria are satisfied by qualifying evidence.

### Recovery
Retry, replan, fallback, compensate, rollback, escalate, pause or abort.

### Human Control
Ask, inform, approve, override, takeover, pause, cancel, revoke, resume.

## Candidate invariants
- Complete(M) should not imply Verified(M).
- Verified(M) requires satisfied acceptance criteria.
- Protected Action(a) requires Authorized(a, mission/context).
- Claim(c) requires qualifying evidence when the mission requires evidence.
- Failure must transition into recover, escalate, block or abort rather than silent success.
- Mission mutation must be versioned and must trigger re-evaluation of affected authority, budget and assurance.

## Architecture
Human intent
→ Mission contract
→ State + authority + budget
→ Capability resolution
→ Execution
→ Trajectory
→ Assurance
→ Evidence
→ Verified outcome
→ Recovery/adaptation as needed
