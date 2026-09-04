# State, Context, Memory and Trajectory

## State decomposition
At minimum:
- Mission State
- External/World State
- Runtime State
- Agent State
- Memory State

## State challenges
- versioning
- stale observations
- optimistic concurrency
- snapshots
- event sourcing
- conflict resolution
- causal ordering
- multi-agent parallel execution

## Context model
Context should distinguish:
- available vs required
- trusted vs untrusted
- ephemeral vs persistent
- provenance
- freshness
- context budget
- user consent

Conversation must not be treated as the authoritative state database.

## Memory
Potential namespaces:
- working
- mission
- episodic
- semantic
- organizational
- user

Each needs:
read/write authority, TTL, provenance, trust, consent, retention, deletion and poisoning defenses.

## Trajectory
Trajectory is a machine-readable execution record, not merely logs.

Candidate events:
mission.created
mission.updated
observation.received
decision.proposed
capability.resolved
capability.invoked
capability.returned
authority.checked
authority.denied
state.changed
human.requested
human.approved
verification.started
verification.completed
evidence.attached
recovery.started

## Human-facing abstraction
Users should see semantic progress:
“tests passed”, “security verification running”, “needs approval”
rather than raw event spam.

## Causal/evidence graph
Sequence alone does not establish causation.
Need ability to represent:
action → artifact → verifier → claim.
