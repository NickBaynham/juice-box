# ADR-0005: One real provider plus a fake provider in the MVP

## Status

Accepted — 2026-08-14. Resolves the conflict between spec section 24
(support at least one LLM provider), section 22 (OpenAI and Anthropic as
initial providers), and section 23 (both provider modules scaffolded).

## Context

Section 24 requires at least one provider. Section 22 names two as
initial. Section 23 scaffolds `providers/openai.py` and
`providers/anthropic.py`. Section 29 lists "dozens of LLM providers" as a
non-goal but says nothing about two.

Shipping two real providers in the MVP doubles the integration surface
that has to be tested against live APIs — tool-call formats, streaming,
token accounting, and error taxonomies all differ — while proving nothing
the architecture does not already assert.

Shipping one provider carries the opposite risk: a single implementation
behind an interface tends to leak that implementation's shape, and the
provider-agnostic principle in section 3 becomes untestable.

## Decision

The MVP ships two implementations of the provider interface, one real and
one fake.

- `src/juicebox/providers/base.py` defines the provider protocol:
  message construction, tool-call request and result exchange, stop
  reasons, and token usage reporting.
- `src/juicebox/providers/anthropic.py` is the real MVP provider.
- `src/juicebox/providers/fake.py` is a scripted provider that returns a
  predetermined sequence of tool calls and text. It is a first-class
  module, not a test fixture, and is selectable as
  `provider: fake` in an agent definition.

The fake provider is what keeps the abstraction honest: the execution
loop, task management, event emission, and the entire acceptance-test
harness run against it with no network access and deterministic output.
Any provider-specific concept that leaks into the loop breaks the fake
first.

`src/juicebox/providers/openai.py` is not written in the MVP. It is the
first Phase 2 item, and adding it with no change to the execution loop is
the test of whether the abstraction held.

Section 22 is amended: Anthropic is the initial provider; OpenAI moves to
Phase 2. Section 23 is amended to add `providers/fake.py`.

## Consequences

- Unit, integration, and end-to-end tests run offline and deterministically
  against the fake provider, with no API key and no token spend.
- Only one live provider integration must be kept working during MVP
  development.
- The provider protocol is exercised by two implementations from day one,
  so the abstraction is validated rather than assumed.
- Anthropic-specific behavior may still bias the protocol design. Adding
  OpenAI in Phase 2 is the explicit check on that, and any resulting
  protocol change is expected to be a Phase 2 cost.
