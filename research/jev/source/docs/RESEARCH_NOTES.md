# Research notes and implementation mapping

## Supplied working note

The supplied September 2026 image, `docs/reference/jev-engineering-working-note.jpeg`, frames a coding loop around five narrow decisions:

1. **Which files?** — `Score` over candidate chunks.
2. **Which model?** — `Choice` over model tiers.
3. **Safe to run?** — a bounded risk judgment before tool execution, with irreversible actions escalating to a person.
4. **Done?** — judge fresh test output rather than the coding agent's self-summary.
5. **Keep or drop?** — `Score` tool output for compaction while preserving survivors rather than rewriting them into a lossy summary.

The package implements those five decision surfaces directly. The decision ABI can be backed by TypeSafe Jev or by OpenAI GPT-5.6 Sol; the typed shapes stay the same.

## Aftergraph mapping

The implementation also follows existing Aftergraph research constraints:

- `Complete(M) != Verified(M)` is represented as a real state-machine boundary: model final text starts verification; it never directly yields `VERIFIED`.
- Authority is purpose/policy controlled outside model cognition. Jev predicts; deterministic policy authorizes.
- Existing protocols are composed instead of reinvented: provider transport is native Responses, OpenAI-compatible, or LiteLLM rather than a new LLM protocol.
- Model/provider/version is explicit runtime state and can be persisted in the audit.
- Cost/context pressure matters: only scoped files enter initial frontier context, and long tool results get a typed retention gate.

## External implementation sources checked for v1.0.0

Evidence cut: 24 September 2026.

- TypeSafe Swagger: `https://api.typesafe.ai/docs` — live System One endpoint and model discovery surface.
- TypeSafe launch note: `https://typesafe.ai/blog/introducing-system-one-models-and-jev` — System One/Jev design and typed-decision framing. Vendor performance claims are treated as vendor claims, not reproduced facts.
- OpenAI API model docs: `https://developers.openai.com/api/docs/models` — current flagship model identifier, frontier capability, Responses/tool support.
- OpenAI Responses/model docs: `https://developers.openai.com/api/docs/models` and model guidance — `gpt-5.6-sol` is the current flagship model for complex reasoning/coding and supports function calling through Responses.
- Anthropic model docs: `https://platform.claude.com/docs/en/models/overview` — `claude-fable-5` is the highest-capability widely released Claude tier and `claude-opus-5` targets long-running agentic coding/knowledge work.
- Google model docs: `https://ai.google.dev/gemini-api/docs/models` — `gemini-3.8-flash` targets long-horizon software engineering/agents and supports function calling.
- LiteLLM docs: `https://docs.litellm.ai/docs/` — unified interface across 100+ LLMs and provider routing/gateway patterns.

## What is verified locally vs not

Verified locally in this release:

- typed request/response adapters using HTTP mock transports;
- provider tool-call continuation for native Responses and OpenAI-compatible chat;
- frontier eligibility filtering before typed model `Choice`;
- workspace confinement and deterministic command boundaries;
- provider credential stripping from worker subprocesses;
- end-to-end local coding loop ending in fresh independent pytest evidence;
- offline demo, config smoke, compile, package integrity.

Not verified in this environment:

- live TypeSafe API behavior with a real account/key;
- live GPT-5.6 Sol generation with a real OpenAI key;
- live third-party provider execution through every LiteLLM adapter;
- network catalog synchronization.

Those require provider credentials and outbound network availability. The package does not label mocked contract tests as live-provider evidence.
